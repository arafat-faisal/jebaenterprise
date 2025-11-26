from django.core.mail import send_mail
from django.template.loader import render_to_string, get_template
from io import BytesIO
from xhtml2pdf import pisa # Requires xhtml2pdf to be installed
from django.conf import settings

# Used by jeba_sales/views.py (checkout)
def send_order_email(sale, recipient_email, current_domain):
    """Sends an order confirmation email."""
    subject = f'Your Order {sale.order_id} is Confirmed!'
    html_message = render_to_string('jeba_core/email/order_confirmation.html', {'sale': sale, 'domain': current_domain})
    send_mail(subject, '', settings.DEFAULT_FROM_EMAIL, [recipient_email], html_message=html_message)

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