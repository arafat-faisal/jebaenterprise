from django.core.mail import EmailMultiAlternatives # Changed from send_mail
from django.template.loader import render_to_string, get_template
from django.conf import settings
from email.mime.image import MIMEImage # For embedding images
import os # For file path operations
from io import BytesIO
from xhtml2pdf import pisa # Requires xhtml2pdf to be installed

# Helper function to embed an image into the email message (from previous step)
def _embed_image_file(email_message, file_path, cid):
    """Opens a file and attaches it to the email message as an inline attachment."""
    if not file_path or not os.path.exists(file_path):
        return
    
    try:
        # Determine MIME type (simplified)
        mimetype = 'image/png' if file_path.lower().endswith('.png') else 'image/jpeg'
        
        with open(file_path, 'rb') as f:
            # Create a MIMEImage object
            img = MIMEImage(f.read(), _subtype=mimetype.split('/')[-1])
            # Set the Content-ID header for inline linking (cid:...)
            img.add_header('Content-ID', f'<{cid}>')
            img.add_header('Content-Disposition', 'inline', filename=os.path.basename(file_path))
            email_message.attach(img)
    except Exception as e:
        # Log error but safely continue sending the email without the image
        print(f"Error embedding image {file_path} for cid:{cid}. Error: {e}")


# Used by jeba_sales/views.py (checkout)
# Signature updated to accept tracking_url instead of current_domain
def send_order_email(sale, recipient_email, tracking_url):
    """Sends an order confirmation email with embedded images and a complete tracking URL."""
    subject = f'Your Order {sale.order_id} is Confirmed!'
    
    # 1. Prepare Email Body and Context
    context = {
        'sale': sale, 
        'tracking_url': tracking_url, # Use the complete URL passed from the view
    }
    html_message = render_to_string('jeba_core/email/order_confirmation.html', context)
    
    # 2. Create the Email Message using EmailMultiAlternatives
    msg = EmailMultiAlternatives(
        subject,
        'Your order has been placed. Please view the HTML version of this email to see product details.', # Text fallback
        settings.DEFAULT_FROM_EMAIL,
        [recipient_email],
    )
    msg.attach_alternative(html_message, "text/html")

    # 3. Embed Logo (cid:logo_img)
    # Assumes logo.png is directly in MEDIA_ROOT
    logo_filename = 'logo.png' 
    # NOTE: You MUST ensure MEDIA_ROOT is correctly configured and the file exists.
    logo_path = os.path.join(settings.MEDIA_ROOT, logo_filename) 
    _embed_image_file(msg, logo_path, 'logo_img')

    # 4. Embed Product Images (cid:img_{{ item.product.id }})
    for item in sale.items.all():
        product_image = item.product.main_image_obj 
        
        if product_image and product_image.image:
            image_file_path = product_image.image.path
            cid_tag = f"img_{item.product.id}"
            _embed_image_file(msg, image_file_path, cid_tag)
            
    # 5. Send the Email
    msg.send()


# Used by jeba_sales/views.py (download_invoice_pdf)
def render_to_pdf(template_src, context_dict={}):
    """Renders a Django template to a PDF file (Requires xhtml2pdf)."""
    template = get_template(template_src)
    html  = template.render(context_dict)
    response = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), response)
    if not pdf.err:
        return response.getvalue()
    return None