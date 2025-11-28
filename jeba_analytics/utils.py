import requests
import time
from django.conf import settings
from jeba_core.models import SiteSettings

def send_capi_event(event_name, event_data, settings_obj):
    """Helper to send event to Facebook Graph API"""
    url = f"https://graph.facebook.com/v19.0/{settings_obj.meta_pixel_id}/events?access_token={settings_obj.meta_access_token}"
    try:
        response = requests.post(url, json=event_data, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"CAPI Error [{event_name}]: {e}")
        return False

def send_add_to_cart_event(product, ip, user_agent, user=None):
    """Sends 'AddToCart' event to Meta CAPI"""
    settings_obj = SiteSettings.load()
    if not settings_obj.meta_access_token or not settings_obj.meta_pixel_id:
        return False

    user_data = {
        "client_ip_address": ip,
        "client_user_agent": user_agent,
    }
    if user and user.is_authenticated and user.email:
        user_data["em"] = user.email

    event_data = {
        "data": [{
            "event_name": "AddToCart",
            "event_time": int(time.time()),
            "action_source": "website",
            "user_data": user_data,
            "custom_data": {
                "currency": "BDT",
                "value": float(product.selling_price),
                "content_ids": [str(product.id)],
                "content_type": "product",
                "content_name": product.name,
            }
        }]
    }
    return send_capi_event("AddToCart", event_data, settings_obj)

def send_purchase_event(sale, ip, user_agent):
    """Sends 'Purchase' event to Meta CAPI"""
    settings_obj = SiteSettings.load()
    if not settings_obj.meta_access_token or not settings_obj.meta_pixel_id:
        return False

    user_data = {
        "fn": sale.customer_name.split()[0],
        "ln": sale.customer_name.split()[-1] if len(sale.customer_name.split()) > 1 else None,
        "ph": sale.phone_number,
        "client_ip_address": ip,
        "client_user_agent": user_agent,
    }
    
    # Add email if available
    if sale.user and sale.user.email:
        user_data["em"] = sale.user.email

    event_data = {
        "data": [{
            "event_name": "Purchase",
            "event_time": int(sale.created_at.timestamp()),
            "action_source": "website",
            "user_data": user_data,
            "custom_data": {
                "currency": "BDT",
                "value": float(sale.total_amount),
                "num_items": len(sale.items.all()),
                "content_ids": [str(item.product_id) for item in sale.items.all()],
                "contents": [{"id": str(item.product_id), "quantity": item.quantity} for item in sale.items.all()],
                "order_id": str(sale.id) # Deduplication key
            }
        }]
    }
    return send_capi_event("Purchase", event_data, settings_obj)