from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string, get_template
from django.conf import settings
from django.contrib.staticfiles import finders
from email.mime.image import MIMEImage
import os
from io import BytesIO
from xhtml2pdf import pisa
from jeba_core.models import SiteSettings
# jeba_analytics.analytics_service is not imported here, removing if not needed or keeping it if it was (it wasn't in original)


def _embed_image_file(email_message, file_path, cid):
    """Opens a file and attaches it to the email message as an inline attachment."""
    if not file_path or not os.path.exists(file_path):
        return
    
    try:
        mimetype = 'image/png' if file_path.lower().endswith('.png') else 'image/jpeg'
        with open(file_path, 'rb') as f:
            img = MIMEImage(f.read(), _subtype=mimetype.split('/')[-1])
            img.add_header('Content-ID', f'<{cid}>')
            img.add_header('Content-Disposition', 'inline', filename=os.path.basename(file_path))
            email_message.attach(img)
    except Exception as e:
        print(f"Error embedding image {file_path} for cid:{cid}. Error: {e}")

def send_order_email(sale, recipient_email, tracking_url):
    """Sends an order confirmation email."""
    subject = f'Your Order {sale.order_id} is Confirmed!'
    context = {'sale': sale, 'tracking_url': tracking_url}
    html_message = render_to_string('jeba_core/email/order_confirmation.html', context)
    
    msg = EmailMultiAlternatives(
        subject,
        'Your order has been placed. Please view the HTML version.',
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email],
    )
    msg.attach_alternative(html_message, "text/html")

    # Embed Logo
    try:
        settings_obj = SiteSettings.load()
        if settings_obj.logo:
            logo_path = settings_obj.logo.path
        else:
            logo_path = os.path.join(settings.MEDIA_ROOT, 'logo.png')
    except:
         logo_path = os.path.join(settings.MEDIA_ROOT, 'logo.png')

    _embed_image_file(msg, logo_path, 'logo_img')

    # Embed Product Images
    for item in sale.items.all():
        product_image = item.product.main_image_obj 
        if product_image and product_image.image:
            image_file_path = product_image.image.path
            cid_tag = f"img_{item.product.id}"
            _embed_image_file(msg, image_file_path, cid_tag)
            
    msg.send()

# --- NEW: Helper for xhtml2pdf to find images ---
def fetch_resources(uri, rel):
    """
    Converts relative URLs (e.g. /media/logo.png) to absolute system paths
    so xhtml2pdf can read the files.
    """
    path = None
    
    # 1. Handle Media Files
    if settings.MEDIA_URL and uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    
    # 2. Handle Static Files
    elif settings.STATIC_URL and uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
        if not os.path.exists(path):
            # Fallback for development if STATIC_ROOT isn't collected
            path = finders.find(uri.replace(settings.STATIC_URL, ""))

    # 3. Handle Absolute Paths (if any)
    else:
        path = os.path.join(settings.BASE_DIR, uri)

    return path if path and os.path.exists(path) else ''

def render_to_pdf(template_src, context_dict={}):
    """Renders a Django template to a PDF file."""
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    
    # Pass the link_callback to handle images
    pdf = pisa.pisaDocument(
        BytesIO(html.encode("UTF-8")), 
        result,
        link_callback=fetch_resources
    )
    
    if not pdf.err:
        return result.getvalue()
    return None