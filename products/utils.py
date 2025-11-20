from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from email.mime.image import MIMEImage
import os

# --- NEW IMPORTS FOR SCRAPER ---
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests
import imagehash
from PIL import Image
from io import BytesIO
from thefuzz import fuzz
import logging

# Get logger
logger = logging.getLogger(__name__)

def send_order_email(sale, user_email):
    subject = f"Order Confirmed: {sale.order_id}"
    from_email = settings.EMAIL_HOST_USER
    to_email = [user_email]

    # 1. Render Template
    html_content = render_to_string('products/email/order_confirmation.html', {'sale': sale})
    text_content = strip_tags(html_content)

    # 2. Create Email Object
    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    msg.attach_alternative(html_content, "text/html")

    # 3. EMBED LOGO (logo.png)
    logo_path = os.path.join(settings.MEDIA_ROOT, 'logo.png') 
    
    if os.path.exists(logo_path):
        try:
            with open(logo_path, 'rb') as f:
                logo_data = f.read()
            
            logo = MIMEImage(logo_data)
            logo.add_header('Content-ID', '<logo_img>')
            logo.add_header('Content-Disposition', 'inline', filename='logo.png')
            msg.attach(logo)
        except Exception as e:
            print(f"Could not attach logo: {e}")

    # 4. Embed Product Images
    for item in sale.items.all():
        if item.product.images.first():
            img_obj = item.product.images.first()
            try:
                img_path = img_obj.image.path
                with open(img_path, 'rb') as f:
                    image_data = f.read()
                image = MIMEImage(image_data)
                image.add_header('Content-ID', f'<img_{item.product.id}>')
                image.add_header('Content-Disposition', 'inline', filename=os.path.basename(img_path))
                msg.attach(image)
            except Exception as e:
                print(f"Could not attach image for {item.product.name}: {e}")

    # 5. Send
    msg.send()

# --- NEW HELPER: AUTO SCRAPER FUNCTION ---
def fetch_competitor_data(product, search_term=None):
    """
    Runs the Playwright scraper for a single product.
    Returns a dict with status and results.
    """
    from .models import CompetitorPrice  # Local import to avoid circular dependency

    if not search_term:
        search_term = product.name

    # AI Thresholds
    IMAGE_WEIGHT = 0.2
    TEXT_WEIGHT = 0.8
    CONFIDENCE_THRESHOLD = 65
    TEXT_SLAM_DUNK = 85

    try:
        # 1. Load Local Images & Hashes
        local_images = product.images.all()
        if not local_images:
            return {'success': False, 'error': 'No local images found'}

        local_hashes = []
        for img in local_images:
            try:
                with open(img.image.path, 'rb') as f:
                    local_image_pil = Image.open(f)
                    local_hashes.append(imagehash.phash(local_image_pil))
            except Exception as e:
                logger.warning(f"Could not load local image {img.id}: {e}")

        if not local_hashes:
            return {'success': False, 'error': 'Could not process local images'}

        # 2. Run Playwright
        results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            search_url = f"https://www.daraz.com.bd/catalog/?q={search_term.replace(' ', '+')}"
            page.goto(search_url, timeout=25000)
            
            try:
                page.wait_for_selector('[data-qa-locator="product-item"]', timeout=10000)
                # Scroll to load lazy images
                for i in range(5):
                    page.evaluate("window.scrollBy(0, window.innerHeight)")
                    page.wait_for_timeout(500)
            except:
                pass # If wait fails, scrape whatever loaded

            html_content = page.content()
            browser.close()

        # 3. Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        product_items = soup.find_all(attrs={'data-qa-locator': 'product-item'})

        for item in product_items:
            try:
                name_link_tag = item.find('div', class_='RfADt').find('a')
                price_span = item.find('div', class_='aBrP0').find('span', class_='ooOxS')
                image_tag = item.find('img')

                # Extract Image URL
                image_url = None
                if image_tag:
                    if image_tag.get('data-src'): image_url = image_tag['data-src']
                    elif image_tag.get('srcset'): image_url = image_tag['srcset'].split(',')[0].split(' ')[0]
                    else: image_url = image_tag.get('src')

                if not all([name_link_tag, price_span, image_url]): continue
                if image_url.startswith('//'): image_url = 'https:' + image_url
                if image_url.startswith('data:'): continue

                scraped_name = name_link_tag.text.strip()
                scraped_url = "https:" + name_link_tag['href']
                scraped_price = price_span.text.replace('৳', '').replace(',', '').strip()

                # 4. Calculate Scores
                # Image Score
                try:
                    resp = requests.get(image_url, timeout=5)
                    scraped_img = Image.open(BytesIO(resp.content))
                    scraped_hash = imagehash.phash(scraped_img)
                    
                    min_dist = 64
                    for lh in local_hashes:
                        dist = lh - scraped_hash
                        if dist < min_dist: min_dist = dist
                    
                    image_score = (1 - min_dist / 64) * 100
                except:
                    image_score = 0 # Fail safe

                # Text Score
                text_score = fuzz.ratio(product.name.lower(), scraped_name.lower())

                # Final Score
                confidence_score = (image_score * IMAGE_WEIGHT) + (text_score * TEXT_WEIGHT)

                if (confidence_score >= CONFIDENCE_THRESHOLD) or (text_score >= TEXT_SLAM_DUNK):
                    results.append({
                        'name': scraped_name,
                        'price': float(scraped_price),
                        'match_score': confidence_score
                    })

            except Exception as e:
                continue

        # 5. Save Results
        if results:
            prices = [r['price'] for r in results]
            min_p = min(prices)
            max_p = max(prices)

            CompetitorPrice.objects.update_or_create(
                product=product,
                website_name="Daraz",
                defaults={
                    'min_price': min_p,
                    'max_price': max_p
                }
            )
            return {'success': True, 'min': min_p, 'max': max_p, 'count': len(results)}
        else:
            return {'success': True, 'count': 0, 'message': 'No matches found'}

    except Exception as e:
        logger.error(f"Scraping error for {product.name}: {e}")
        return {'success': False, 'error': str(e)}