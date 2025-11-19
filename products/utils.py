from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from email.mime.image import MIMEImage
import os
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
    # This assumes you saved 'logo.png' in your media folder
    logo_path = os.path.join(settings.MEDIA_ROOT, 'logo.png') 
    
    if os.path.exists(logo_path):
        try:
            with open(logo_path, 'rb') as f:
                logo_data = f.read()
            
            logo = MIMEImage(logo_data)
            logo.add_header('Content-ID', '<logo_img>') # We refer to this ID in the HTML
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