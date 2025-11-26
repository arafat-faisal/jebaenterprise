import requests
from django.conf import settings
from jeba_core.models import SiteSettings # Necessary for getting pixel/token

def send_purchase_event(sale, request):
    """Sends a Purchase event to the Meta Conversions API (CAPI)."""
    settings_obj = SiteSettings.load()
    
    if not settings_obj.meta_access_token or not settings_obj.meta_pixel_id:
        return False

    # Build Purchase event payload (simplified for example)
    event_data = {
        "data": [{
            "event_name": "Purchase",
            "event_time": int(sale.created_at.timestamp()),
            "user_data": {
                "fn": sale.customer_name.split()[0],
                "ln": sale.customer_name.split()[-1] if len(sale.customer_name.split()) > 1 else None,
                "ph": sale.phone_number,
                "em": sale.user.email if sale.user and sale.user.email else None,
                "external_id": sale.user.id if sale.user else None,
                "client_ip_address": request.META.get('REMOTE_ADDR'),
                "client_user_agent": request.META.get('HTTP_USER_AGENT'),
            },
            "custom_data": {
                "currency": "BDT",
                "value": float(sale.total_amount),
                "num_items": len(sale.items.all()),
                "content_ids": [str(item.product_id) for item in sale.items.all()],
                "contents": [{"id": str(item.product_id), "quantity": item.quantity} for item in sale.items.all()],
            },
            "action_source": "website",
        }]
    }

    url = f"https://graph.facebook.com/v19.0/{settings_obj.meta_pixel_id}/events?access_token={settings_obj.meta_access_token}"

    try:
        response = requests.post(url, json=event_data, timeout=5)
        return response.status_code == 200
    except Exception:
        return False