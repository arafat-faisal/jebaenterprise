from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from email.mime.image import MIMEImage
import os
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib.staticfiles import finders

# --- IMPORTS FOR SCRAPER ---
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests
import imagehash
from PIL import Image
from io import BytesIO
from thefuzz import fuzz
import logging

# --- MODULAR IMPORTS ---
# We import models here to ensure they are available for the logic below
from jeba_intelligence.models import CompetitorPrice
# -----------------------

# Get logger
logger = logging.getLogger(__name__)

# --- HELPER: Attach Logo ---
def attach_logo(msg):
    """Helper to attach the logo to an email message."""
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
    return msg

def send_order_email(sale, user_email, domain='jebaenterprise.com'):
    subject = f"Order Confirmed: {sale.order_id}"
    from_email = settings.EMAIL_HOST_USER
    to_email = [user_email]

    # Create the tracking link
    # If domain doesn't start with http, add it (assuming https for production, http for local)
    protocol = "https" if "jeba" in domain else "http"
    tracking_url = f"{protocol}://{domain}/track-order/{sale.access_token}/"

    # Pass tracking_url to the template
    context = {
        'sale': sale,
        'tracking_url': tracking_url
    }

    html_content = render_to_string('products/email/order_confirmation.html', context)
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    msg.attach_alternative(html_content, "text/html")

    msg = attach_logo(msg)

    # Attach Product Images
    for item in sale.items.all():
        # Accessing product via the foreign key (works across apps)
        main_img = item.product.images.filter(is_main=True).first()
        if not main_img:
            main_img = item.product.images.first()
            
        if main_img:
            try:
                img_path = main_img.image.path
                with open(img_path, 'rb') as f:
                    image_data = f.read()
                image = MIMEImage(image_data)
                image.add_header('Content-ID', f'<img_{item.product.id}>')
                image.add_header('Content-Disposition', 'inline', filename=os.path.basename(img_path))
                msg.attach(image)
            except Exception as e:
                print(f"Could not attach image for {item.product.name}: {e}")

    msg.send()

# --- Send Welcome Email ---
def send_welcome_email(user):
    subject = f"Welcome to Jeba Enterprise, {user.first_name}!"
    from_email = settings.EMAIL_HOST_USER
    to_email = [user.email]

    html_content = render_to_string('products/email/welcome.html', {'user': user})
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    msg.attach_alternative(html_content, "text/html")
    
    # Attach Logo
    msg = attach_logo(msg)
    
    msg.send()

# --- SCRAPER FUNCTION ---
def fetch_competitor_data(product, search_term=None, manual_image_bytes=None, save_to_db=True,
                          image_weight=0.3, text_weight=0.7, confidence_threshold=60,
                          text_slam_dunk=85, image_slam_dunk=90):
    """
    Runs the Playwright scraper for a single product.
    Accepts custom thresholds and weights.
    """
    
    if not search_term:
        search_term = product.name

    # Use passed arguments for configuration
    IMAGE_WEIGHT = float(image_weight)
    TEXT_WEIGHT = float(text_weight)
    CONFIDENCE_THRESHOLD = int(confidence_threshold)
    TEXT_SLAM_DUNK = int(text_slam_dunk)
    IMAGE_SLAM_DUNK = int(image_slam_dunk)

    try:
        local_hashes = []

        # 1. Use Manual Image if provided
        if manual_image_bytes:
            try:
                manual_img = Image.open(BytesIO(manual_image_bytes))
                local_hashes.append(imagehash.phash(manual_img))
            except Exception as e:
                logger.warning(f"Failed to process manual image: {e}")
        
        # 2. If no manual image, load Product Images
        if not local_hashes:
            local_images = product.images.all()
            for img in local_images:
                try:
                    with open(img.image.path, 'rb') as f:
                        local_image_pil = Image.open(f)
                        local_hashes.append(imagehash.phash(local_image_pil))
                except Exception as e:
                    logger.warning(f"Could not load local image {img.id}: {e}")

        # 3. Run Playwright
        results = []
        has_images = len(local_hashes) > 0

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Standard User Agent to avoid detection
            page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Search Daraz
            search_url = f"https://www.daraz.com.bd/catalog/?q={search_term.replace(' ', '+')}"
            page.goto(search_url, timeout=30000)
            
            try:
                page.wait_for_selector('[data-qa-locator="product-item"]', timeout=8000)
                # Quick scroll to trigger lazy loading
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, window.innerHeight)")
                    page.wait_for_timeout(500)
            except:
                pass 

            html_content = page.content()
            browser.close()

        # 4. Parse & Compare
        soup = BeautifulSoup(html_content, 'html.parser')
        product_items = soup.find_all(attrs={'data-qa-locator': 'product-item'})

        for item in product_items:
            try:
                name_link_tag = item.find('div', class_='RfADt').find('a')
                price_span = item.find('div', class_='aBrP0').find('span', class_='ooOxS')
                image_tag = item.find('img')

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
                scraped_price_str = price_span.text.replace('৳', '').replace(',', '').strip()
                
                try:
                    scraped_price = float(scraped_price_str)
                except:
                    continue

                # -- Image Match --
                image_score = 0
                if has_images:
                    try:
                        resp = requests.get(image_url, timeout=3) 
                        scraped_img = Image.open(BytesIO(resp.content))
                        scraped_hash = imagehash.phash(scraped_img)
                        
                        min_dist = 64
                        for lh in local_hashes:
                            dist = lh - scraped_hash
                            if dist < min_dist: min_dist = dist
                        
                        image_score = (1 - min_dist / 64) * 100
                    except:
                        pass

                # -- SMARTER TEXT MATCHING --
                text_score_token = fuzz.token_set_ratio(product.name.lower(), scraped_name.lower())
                text_score_partial = fuzz.partial_ratio(product.name.lower(), scraped_name.lower())
                text_score = max(text_score_token, text_score_partial)

                # -- Final Score Calculation --
                confidence_score = (image_score * IMAGE_WEIGHT) + (text_score * TEXT_WEIGHT)

                # -- Selection Logic --
                is_visual_match = (image_score >= IMAGE_SLAM_DUNK and text_score > 40)
                
                if (confidence_score >= CONFIDENCE_THRESHOLD) or (text_score >= TEXT_SLAM_DUNK) or is_visual_match:
                    results.append({
                        'name': scraped_name,
                        'price': scraped_price,
                        'url': scraped_url,
                        'image_url': image_url,
                        'match_score': round(confidence_score, 1),
                        'text_score': text_score,
                        'image_score': round(image_score, 1)
                    })

            except Exception as e:
                continue
        
        # Sort by Match Score
        results.sort(key=lambda x: x['match_score'], reverse=True)

        # 5. Handle Results
        min_p = 0
        max_p = 0
        
        if results:
            prices = [r['price'] for r in results]
            min_p = min(prices)
            max_p = max(prices)

            if save_to_db:
                # Updated to use the correct model from jeba_intelligence
                CompetitorPrice.objects.update_or_create(
                    product=product,
                    website_name="Daraz",
                    defaults={
                        'min_price': min_p,
                        'max_price': max_p
                    }
                )
        
        return {
            'success': True, 
            'min': min_p, 
            'max': max_p, 
            'count': len(results),
            'results': results 
        }

    except Exception as e:
        logger.error(f"Scraping error for {product.name}: {e}")
        return {'success': False, 'error': str(e)}
    
def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those resources
    """
    result = finders.find(uri)
    if result:
        if not isinstance(result, (list, tuple)):
            result = [result]
        result = list(set(result))
        path = result[0]
    else:
        sUrl = settings.STATIC_URL        # Typically /static/
        sRoot = settings.STATIC_ROOT      # Typically /home/userX/project_static/
        mUrl = settings.MEDIA_URL         # Typically /media/
        mRoot = settings.MEDIA_ROOT       # Typically /home/userX/project_media/

        if uri.startswith(mUrl):
            path = os.path.join(mRoot, uri.replace(mUrl, ""))
        elif uri.startswith(sUrl):
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        else:
            return uri

    # Make sure that file exists
    if not os.path.isfile(path):
            # It's better to just return the URI if file not found rather than crashing the PDF
            print(f"PDF warning: Missing file {path}")
            return uri 
    return path

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, link_callback=link_callback)
    if not pdf.err:
        return result.getvalue() # Return bytes, not HttpResponse, to keep it flexible
    return None