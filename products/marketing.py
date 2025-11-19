import requests
import hashlib
import time
from django.conf import settings
from .models import SiteSettings

def hash_data(data):
    """Facebook requires data to be sha256 hashed."""
    if not data:
        return None
    return hashlib.sha256(data.strip().lower().encode('utf-8')).hexdigest()

def send_purchase_event(sale, request=None):
    """
    Sends a 'Purchase' event to Facebook Conversions API.
    """
    site_settings = SiteSettings.load()
    pixel_id = site_settings.meta_pixel_id
    access_token = site_settings.meta_access_token

    if not pixel_id or not access_token:
        return # Skip if keys are missing

    url = f"https://graph.facebook.com/v19.0/{pixel_id}/events"
    
    # 1. User Data (Hashed for privacy)
    user_data = {
        "ph": [hash_data(sale.phone_number)],
        "ct": [hash_data("dhaka")], # You can make this dynamic if you split city from address
        "country": [hash_data("bd")]
    }
    
    # If we have a logged-in user email, use it
    if sale.user and sale.user.email:
        user_data["em"] = [hash_data(sale.user.email)]
    
    # Add Browser ID (fbp) and Click ID (fbc) if available in cookies
    if request:
        if '_fbp' in request.COOKIES:
            user_data['fbp'] = request.COOKIES['_fbp']
        if '_fbc' in request.COOKIES:
            user_data['fbc'] = request.COOKIES['_fbc']
        user_data['client_ip_address'] = request.META.get('REMOTE_ADDR')
        user_data['client_user_agent'] = request.META.get('HTTP_USER_AGENT')

    # 2. Construct Payload
    payload = {
        "data": [
            {
                "event_name": "Purchase",
                "event_time": int(time.time()),
                "action_source": "website",
                "event_id": sale.order_id, # UNIQUE ID for Deduplication
                "user_data": user_data,
                "custom_data": {
                    "currency": "BDT",
                    "value": float(sale.total_amount),
                    "content_ids": [str(item.product.id) for item in sale.items.all()],
                    "content_type": "product",
                    "order_id": sale.order_id
                }
            }
        ],
        "access_token": access_token
    }

    # 3. Send (Fire & Forget)
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"CAPI Error: {e}")