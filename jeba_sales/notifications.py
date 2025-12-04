import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_telegram_order_notification(sale):
    """
    Sends a formatted message to the admin via Telegram when a new order is placed.
    """
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)

    if not token or not chat_id:
        logger.warning("Telegram settings not configured. Skipping notification.")
        return

    # Format the message
    items_list = ""
    for item in sale.items.all():
        items_list += f"• {item.product.name} (x{item.quantity})\n"

    message = (
        f"🚨 **NEW ORDER RECEIVED!** 🚨\n\n"
        f"**Order ID:** {sale.invoice_number}\n"
        f"**Customer:** {sale.customer_name}\n"
        f"**Amount:** ৳{sale.total_amount:,.2f}\n"
        f"**Payment:** {sale.get_payment_method_display()}\n\n"
        f"📦 **Items:**\n{items_list}\n"
        f"🚚 **Area:** {'Outside Dhaka' if sale.delivery_charge > 60 else 'Inside Dhaka'}\n"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        logger.info(f"Telegram notification sent for Order {sale.id}")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")