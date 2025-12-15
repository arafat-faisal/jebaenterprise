from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.mime.image import MIMEImage
import os
from jeba_core.models import SiteSettings

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

def send_welcome_email(user):
    """Sends a welcome email to the new user (Used in register_view)."""
    subject = 'Welcome to Jeba Enterprise!'
    html_message = render_to_string('jeba_core/email/welcome.html', {'user': user})
    
    msg = EmailMultiAlternatives(
        subject,
        'Welcome to Jeba Enterprise! Your account has been created.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
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
    
    msg.send()