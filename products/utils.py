from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from email.mime.image import MIMEImage
import os

def send_order_email(sale, user_email):
    subject = f"Order Confirmed: #{sale.id}"
    from_email = settings.EMAIL_HOST_USER
    to_email = [user_email]

    # 1. Render Template
    html_content = render_to_string('products/email/order_confirmation.html', {'sale': sale})
    text_content = strip_tags(html_content)

    # 2. Create Email Object
    msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    msg.attach_alternative(html_content, "text/html")

    # 3. Embed Product Images
    # We loop through items and attach their images if they exist
    for item in sale.items.all():
        if item.product.images.first():
            img_obj = item.product.images.first()
            try:
                # Get the path to the file on disk
                img_path = img_obj.image.path
                
                with open(img_path, 'rb') as f:
                    image_data = f.read()
                
                # Create MIMEImage
                image = MIMEImage(image_data)
                
                # Define a unique Content-ID (cid)
                # We use the product ID to make it unique: 'img_123'
                image.add_header('Content-ID', f'<img_{item.product.id}>')
                image.add_header('Content-Disposition', 'inline', filename=os.path.basename(img_path))
                
                msg.attach(image)
            except Exception as e:
                print(f"Could not attach image for {item.product.name}: {e}")

    # 4. Send
    msg.send()