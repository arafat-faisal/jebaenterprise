import requests
import json
import logging
from django.conf import settings
from typing import TYPE_CHECKING
from decimal import Decimal

# --- SETUP LOGGING ---
logger = logging.getLogger('products')

if TYPE_CHECKING:
    from jeba_sales.models import Sale

# --- CONFIGURATION ---
API_KEY = getattr(settings, 'STEADFAST_API_KEY', '')
SECRET_KEY = getattr(settings, 'STEADFAST_SECRET_KEY', '')
BASE_URL = getattr(settings, 'STEADFAST_BASE_URL', 'https://portal.packzy.com/api/v1')

def make_payload(sale: 'Sale'):
    """Extracts data from a Sale object to prep the form."""
    return {
        "invoice": sale.invoice_number,
        "recipient_name": sale.customer_name,
        "recipient_phone": sale.phone_number,
        "recipient_address": sale.shipping_address,
        "cod_amount": int(sale.total_amount),
        "note": "Handle with care"
    }

def create_steadfast_order(sale: 'Sale'):
    payload = make_payload(sale)
    return submit_steadfast_order(payload)

def submit_steadfast_order(payload):
    """
    Sends the dictionary payload to Steadfast API.
    Fixes TypeError: Object of type Decimal is not JSON serializable.
    """
    url = f"{BASE_URL}/create_order"
    
    headers = {
        'Api-Key': API_KEY,
        'Secret-Key': SECRET_KEY,
        'Content-Type': 'application/json'
    }

    # --- FIX: Convert Decimal to Float/Int for JSON Serialization ---
    # Create a copy of the payload to modify
    api_payload = payload.copy()
    
    # Check if cod_amount is a Decimal object and convert it to a float
    if isinstance(api_payload.get('cod_amount'), Decimal):
        api_payload['cod_amount'] = float(api_payload['cod_amount'])
    # Optional: Convert to integer if Steadfast strictly requires no decimal places
    # api_payload['cod_amount'] = int(api_payload['cod_amount']) 
    # We use float to be safe with currency but int(round()) is also common.

    # LOGGING: Request Details (Use the converted payload)
    logger.info(f"STEADFAST CREATE REQUEST: {url} | Payload: {json.dumps(api_payload)}")

    try:
        # Use the converted payload for the actual API call
        response = requests.post(url, json=api_payload, headers=headers, timeout=10)
        
        logger.info(f"STEADFAST CREATE RESPONSE [{response.status_code}]: {response.text}")
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            return {'success': False, 'error': f"Invalid JSON: {response.text}"}

        if response.status_code == 200 and data and data.get('status') == 200:
            return {
                'success': True,
                'consignment_id': data['consignment']['consignment_id'],
                'tracking_code': data['consignment']['tracking_code'],
                'status': data['consignment']['status']
            }
        else:
            error_msg = data.get('error') or str(data)
            return {'success': False, 'error': error_msg}
            
    except Exception as e:
        logger.exception("Steadfast Create Error")
        return {'success': False, 'error': str(e)}

def check_delivery_status(consignment_id, invoice_number=None):
    """
    Checks delivery status.
    Feature: Falls back to Invoice Check if Consignment ID returns 'unknown'.
    """
    if not consignment_id:
        return None

    headers = {
        'Api-Key': API_KEY,
        'Secret-Key': SECRET_KEY,
        'Content-Type': 'application/json'
    }

    # --- ATTEMPT 1: Check by Consignment ID (the default method) ---
    url_cid = f"{BASE_URL}/status_by_cid/{consignment_id}"
    logger.info(f"STEADFAST CHECK CID [{consignment_id}]: {url_cid}")

    status = _fetch_status(url_cid, headers, "CID")
    
    # If found and not 'unknown', return it immediately
    if status and status != 'unknown':
        return status

    # --- ATTEMPT 2: Fallback to Invoice Number ---
    if invoice_number:
        logger.warning(f"Steadfast CID returned '{status}'. Retrying with Invoice: {invoice_number}")
        # The endpoint for checking by invoice is /status_by_invoice/{invoice_number}
        url_inv = f"{BASE_URL}/status_by_invoice/{invoice_number}"
        
        invoice_status = _fetch_status(url_inv, headers, "INVOICE")
        if invoice_status and invoice_status != 'unknown':
            logger.info(f"Steadfast Recovered Status via Invoice: {invoice_status}")
            return invoice_status
        else:
             logger.warning("Invoice lookup failed or also returned 'unknown'.")


    return status # Returns 'unknown' or None if all attempts fail

def _fetch_status(url, headers, check_type):
    """Helper function to perform the GET request and normalize status."""
    try:
        response = requests.get(url, headers=headers, timeout=5)
        logger.info(f"STEADFAST {check_type} RESPONSE: {response.text}")

        if response.status_code == 200:
            data = response.json()
            # The API response field may be 'delivery_status' (GET) or 'status' (Webhook)
            raw_status = data.get('delivery_status') or data.get('status')
            
            if raw_status:
                # CRITICAL FIX: Normalize to lowercase for reliable comparison in views.py
                normalized_status = raw_status.lower()
                logger.info(f"Normalized Status: {normalized_status}")
                return normalized_status
            else:
                logger.warning(f"Steadfast response missing expected status field: {data}")
                
        else:
            logger.error(f"Steadfast Status Check Failed [Code {response.status_code}]")

    except Exception as e:
        logger.error(f"Steadfast {check_type} Check Error: {e}")
    
    return None