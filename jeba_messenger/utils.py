import requests
import os
import logging

logger = logging.getLogger(__name__)

FB_PAGE_ACCESS_TOKEN = os.getenv('FB_PAGE_ACCESS_TOKEN')
FB_API_URL = "https://graph.facebook.com/v19.0/me/messages"

def send_facebook_message(psid, text):
    """
    Sends a text message to a specific Facebook user (PSID).
    """
    if not FB_PAGE_ACCESS_TOKEN:
        logger.error("FB_PAGE_ACCESS_TOKEN is missing in .env")
        return False

    headers = {
        'Content-Type': 'application/json'
    }
    
    payload = {
        'recipient': {'id': psid},
        'message': {'text': text},
        'messaging_type': 'RESPONSE'
    }

    try:
        params = {'access_token': FB_PAGE_ACCESS_TOKEN}
        response = requests.post(FB_API_URL, params=params, json=payload)
        
        if response.status_code == 200:
            return True
        else:
            logger.error(f"FB Send Error: {response.text}")
            return False
    except Exception as e:
        logger.error(f"FB Request Failed: {e}")
        return False