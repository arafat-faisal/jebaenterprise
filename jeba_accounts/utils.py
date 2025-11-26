from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

def send_welcome_email(user):
    """Sends a welcome email to the new user (Used in register_view)."""
    subject = 'Welcome to Jeba Enterprise!'
    html_message = render_to_string('jeba_core/email/welcome.html', {'user': user})
    send_mail(subject, '', settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message)