import csv
import ast
import requests
import os
import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from products.models import Product, Category, ProductImage

# --- LOGGING SETUP ---
logging.basicConfig(
    filename='import_fast.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class Command(BaseCommand):
    help = 'SUPER FAST Import with Infinite Retry (Except 404s)'

    def handle(self, *args, **kwargs):
        file_path = 'product_details.csv'
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        # 1. Setup Category
        default_category, _ = Category.objects.get_or_create(name="Imported New")
        
        # 2. Read CSV into Memory
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            rows = list(csv.DictReader(csvfile))
            
        total = len(rows)
        self.stdout.write(f"🚀 Starting 20-Thread Import for {total} products...")

        # 3. The Worker Function (Runs in Parallel)
        def process_row(row):
            try:
                product_name = row['product_name'].strip()
                
                # --- STEP A: Create/Get Product (Database Operation) ---
                # We use get_or_create to ensure we don't duplicate if run twice
                # ... inside process_row ...
                
                product, created = Product.objects.get_or_create(
                    name=product_name,
                    defaults={
                        # --- UPDATED MAPPING ---
                        'short_description': row.get('short_description', ''),
                        'description': row.get('long_description', ''), # Long details go here
                        # -----------------------
                        'category': default_category,
                        'selling_price': 0,
                        'stock_quantity': 10,
                        'call_for_price': True,
                        'is_featured': False
                    }
                )

                # --- STEP B: Handle Images ---
                try:
                    image_list = ast.literal_eval(row['image_urls'])
                except:
                    image_list = []

                # Filter Thumbnails (-150x150 etc)
                clean_urls = [u for u in image_list if not re.search(r'-\d+x\d+\.[a-zA-Z]+$', u)]

                for index, img_url in enumerate(clean_urls):
                    # Check if we already have this image (Resume Logic)
                    # We guess the filename format to check DB
                    try:
                        ext = img_url.split('.')[-1].split('?')[0]
                        if len(ext) > 4 or not ext: ext = 'jpg'
                        expected_name = f"{product.id}-{index}.{ext}"
                        
                        # If image exists in DB, SKIP download
                        if ProductImage.objects.filter(product=product, image__endswith=expected_name).exists():
                            continue
                    except:
                        pass

                    # DOWNLOAD (Infinite Retry)
                    content = self.download_forever(img_url)
                    
                    if content:
                        # Save to DB
                        p_img = ProductImage(product=product)
                        p_img.image.save(expected_name, ContentFile(content))
                        p_img.save()
                
                return f"✅ {product_name}"

            except Exception as e:
                return f"❌ Error processing {row.get('product_name')}: {e}"

        # 4. Run in Parallel (20 Workers = Super Fast)
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = executor.map(process_row, rows)
            
            for i, result in enumerate(results):
                # Print progress every 10 items to keep terminal clean
                if "Error" in result:
                    self.stdout.write(self.style.ERROR(result))
                elif i % 5 == 0:
                    self.stdout.write(self.style.SUCCESS(f"[{i}/{total}] Processing..."))
        
        self.stdout.write(self.style.SUCCESS("🎉 Import Completed!"))

    def download_forever(self, url):
        """
        Retries FOREVER until success or Dead End (404/403).
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        while True:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                
                # SUCCESS
                if response.status_code == 200:
                    return response.content
                
                # DEAD ENDS (Stop retrying)
                elif response.status_code in [404, 403, 410]:
                    logging.warning(f"Dead End ({response.status_code}): {url}")
                    return None 
                
                # SERVER BUSY (Retry)
                else:
                    time.sleep(2) # Wait a bit
                    continue

            except requests.exceptions.RequestException:
                # CONNECTION DIED (Retry)
                time.sleep(2)
                continue
            except Exception:
                return None