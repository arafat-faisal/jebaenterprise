import requests
import json
from django.conf import settings


# --- CONFIGURATION ---
# We now pull these from settings.py, which pulls from .env
API_KEY = settings.STEADFAST_API_KEY
SECRET_KEY = settings.STEADFAST_SECRET_KEY
BASE_URL = settings.STEADFAST_BASE_URL

def make_payload(sale):
    """
    Extracts data from a Sale object to prep the form.
    """
    return {
        "invoice": sale.invoice_number,
        "recipient_name": sale.customer_name,
        "recipient_phone": sale.phone_number,
        "recipient_address": sale.shipping_address,
        "cod_amount": int(sale.total_amount), # Steadfast often prefers Integers for COD
        "note": "Handle with care"
    }

def submit_steadfast_order(payload):
    """
    Sends the dictionary payload to Steadfast API.
    """
    url = f"{BASE_URL}/create_order"
    
    headers = {
        'Api-Key': API_KEY,
        'Secret-Key': SECRET_KEY,
        'Content-Type': 'application/json'
    }

    try:
        # Ensure cod_amount is numeric
        payload['cod_amount'] = float(payload['cod_amount'])
        
        # --- FIX: Added timeout=10 ---
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and 'consignment' in data:
            return {
                'success': True,
                'consignment_id': data['consignment']['consignment_id'],
                'tracking_code': data['consignment']['tracking_code'],
                'status': data['consignment']['status']
            }
        else:
            error_msg = str(data) if data else "Unknown Error"
            return {'success': False, 'error': error_msg}
            
    except requests.exceptions.Timeout:
        return {'success': False, 'error': "Steadfast API timed out. Please try again later."}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# For the "Bulk Action" (uses default data)
def create_steadfast_order(sale):
    payload = make_payload(sale)
    return submit_steadfast_order(payload)

def check_delivery_status(consignment_id):
    url = f"{BASE_URL}/status_by_cid/{consignment_id}"
    headers = {
        'Api-Key': API_KEY,
        'Secret-Key': SECRET_KEY,
        'Content-Type': 'application/json'
    }
    try:
        # --- FIX: Added timeout=5 (shorter timeout for status checks) ---
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200 and 'delivery_status' in response.json():
            return response.json()['delivery_status']
    except:
        pass
    return None