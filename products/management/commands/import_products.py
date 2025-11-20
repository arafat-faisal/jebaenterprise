import csv
import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db import connection, transaction
from django.db.utils import OperationalError
from products.models import Product, Category, ProductImage

# --- LOGGING SETUP ---
logging.basicConfig(
    filename='import_products.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import products with Product-Level Concurrency (Preserves Image Order)'

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, default='product_details.csv', help='Path to CSV file')
        parser.add_argument('--html_dir', type=str, default=r'E:\WebProjects\plan\htmls\product_details', help='Path to HTML folder')
        parser.add_argument('--workers', type=int, default=10, help='Number of products to process at once')

    def handle(self, *args, **options):
        csv_path = options['csv']
        html_dir = options['html_dir']
        max_workers = options['workers']

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'CSV file not found: {csv_path}'))
            return

        # Ensure default category exists (Main Thread)
        default_category, _ = Category.objects.get_or_create(name="Imported Products")

        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
            total_rows = len(rows)

            self.stdout.write(f"🚀 Starting import for {total_rows} products with {max_workers} threads...")

            # --- PRODUCT LEVEL CONCURRENCY ---
            # We process X products at a time. 
            # Inside each thread, images are handled sequentially to keep order.
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.process_single_row, row, html_dir, default_category.id): row 
                    for row in rows
                }

                for i, future in enumerate(as_completed(futures)):
                    try:
                        result = future.result()
                        # Optional: Visual progress bar logic here
                        if i % 5 == 0:
                            self.stdout.write(f"   Processed {i + 1}/{total_rows}...")
                    except Exception as e:
                        logger.error(f"Thread failure: {e}")

            self.stdout.write(self.style.SUCCESS("🎉 Import Process Completed!"))

    def get_plain_text(self, soup_element):
        """Strips ALL HTML tags and returns clean plain text."""
        if not soup_element:
            return ""
        for tag in soup_element(["script", "style"]):
            tag.extract()
        return soup_element.get_text(separator=' ', strip=True)

    def get_long_description(self, soup):
        """Smart logic to find the long description container."""
        div = soup.select_one('.wd-single-content .elementor-widget-container')
        if not div:
            div = soup.select_one('.wd-single-product-content')
        if not div:
            div = soup.select_one('#tab-description')
        if not div:
            div = soup.select_one('.woocommerce-Tabs-panel--description')
        
        # Nuclear Option
        if not div:
            meta_desc = soup.find("meta", property="og:description")
            if meta_desc:
                content = meta_desc.get("content", "")[:50]
                if len(content) > 10:
                    found_text = soup.find(string=lambda text: text and content in text)
                    if found_text:
                        parent = found_text.find_parent('div')
                        if parent and 'elementor-widget-container' not in parent.get('class', []):
                            parent = parent.find_parent('div') 
                        div = parent

        if not div:
            return ""

        # Clean junk tags but keep HTML structure
        for tag in div(["script", "style", "iframe", "button", "input", "form", "noscript"]):
            tag.extract()
        
        return div.decode_contents().strip()

    def process_single_row(self, row, html_dir, category_id):
        """
        This runs inside a THREAD. 
        It handles one single product from start to finish.
        """
        # 1. Fix DB Connection for Threads
        # Django closes connections at end of request, but threads persist. 
        # We must manage connections manually in threads to avoid timeouts/locks.
        connection.close()
        
        filename = row.get('filename', '').strip()
        product_name = row.get('product_name', 'Unknown Product').strip()
        html_path = os.path.join(html_dir, filename)
        
        short_desc_text = ""
        long_desc_html = ""
        image_urls = []

        # --- HTML PARSING ---
        if filename and os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

                # Short Desc (Plain Text)
                short_div = soup.select_one('.woocommerce-product-details__short-description')
                if not short_div:
                    short_div = soup.select_one('.elementor-widget-wd_single_product_short_description')
                short_desc_text = self.get_plain_text(short_div)

                # Long Desc (HTML)
                long_desc_html = self.get_long_description(soup)

                # Images
                gallery_imgs = soup.select('.woocommerce-product-gallery img')
                for img in gallery_imgs:
                    src = img.get('data-large_image') or img.get('data-src') or img.get('src')
                    if src:
                        if src.startswith('//'): src = 'https:' + src
                        if '100x100' not in src and '150x150' not in src: 
                            if src not in image_urls:
                                image_urls.append(src)

        # --- DB SAVE (With Retry Logic for SQLite Locks) ---
        retries = 3
        while retries > 0:
            try:
                # We fetch the category inside the thread to prevent cross-thread object sharing issues
                category = Category.objects.get(id=category_id)
                
                product, created = Product.objects.update_or_create(
                    name=product_name,
                    defaults={
                        'short_description': short_desc_text,
                        'description': long_desc_html,
                        'category': category,
                        'selling_price': 0.00,
                        'stock_quantity': 10,
                        'call_for_price': True
                    }
                )
                break # Success
            except OperationalError:
                # If Database is locked (SQLite), wait and retry
                time.sleep(1)
                retries -= 1
                connection.close()
        
        if retries == 0:
            print(f"❌ DB Lock Error: {product_name}")
            return

        # --- IMAGE DOWNLOADING (SEQUENTIAL) ---
        # We download images strictly one by one HERE inside the thread.
        # This ensures Image 1 is saved before Image 2 for this specific product.
        if image_urls:
            self.download_images_sequentially(product, image_urls)
        
        status_msg = "Created" if created else "Updated"
        print(f"✅ {status_msg}: {product_name}")

    def download_images_sequentially(self, product, urls):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://google.com'
        }
        
        # We iterate with enumeration to force order 0, 1, 2...
        for i, url in enumerate(urls):
            try:
                clean_url = url.split('?')[0]
                ext = os.path.splitext(clean_url)[1].lower()
                if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                    ext = '.jpg'
                
                # Naming convention preserves order visually in file system too
                filename = f"prod_{product.id}_{i}{ext}"

                # Skip if already downloaded
                if ProductImage.objects.filter(product=product, image__icontains=filename).exists():
                    continue

                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    img_instance = ProductImage(product=product)
                    img_instance.image.save(filename, ContentFile(response.content))
                    img_instance.save()
                
                # Small sleep not strictly necessary in threaded logic, 
                # but good to prevent hammering the server too hard per-thread
                time.sleep(0.1) 

            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")