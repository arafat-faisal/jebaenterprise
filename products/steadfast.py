import requests
import json
from django.conf import settings

# --- CONFIGURATION ---
# Replace these with your actual keys from Steadfast
API_KEY = 'qwxkqlw0cf9hxgarhzibhf80ij2qdy1e '
SECRET_KEY = 'h96tjqmj8dobahni0x8amiez '
BASE_URL = 'https://portal.packzy.com/api/v1'


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
        
        response = requests.post(url, json=payload, headers=headers)
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
        response = requests.get(url, headers=headers)
        if response.status_code == 200 and 'delivery_status' in response.json():
            return response.json()['delivery_status']
    except:
        pass
    return None