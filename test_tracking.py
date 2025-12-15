import requests
import json
import time

BASE_URL = "http://127.0.0.1:8080"
SLUG = "demo-offer"

def run_test():
    print(f"1. Visiting Landing Page: {BASE_URL}/landing/{SLUG}/")
    s = requests.Session()
    resp = s.get(f"{BASE_URL}/landing/{SLUG}/")
    
    if resp.status_code != 200:
        print(f"❌ Failed to load page: {resp.status_code}")
        return

    cookie = s.cookies.get('jeba_lid')
    if not cookie:
        print("❌ No 'jeba_lid' cookie received!")
        # Try to extract from set-cookie manually if needed, but requests usually handles it.
        print("Cookies:", s.cookies)
        return
        
    print(f"✅ Session Started. ID: {cookie}")
    
    # 2. Simulate Heartbeat
    track_url = f"{BASE_URL}/landing/api/track/"
    payload = {
        "session_id": cookie,
        "event_type": "HEARTBEAT",
        "metadata": {"test": "script"},
        "value": 0
    }
    
    print(f"2. Sending Heartbeat to {track_url}")
    resp = s.post(track_url, json=payload)
    
    if resp.status_code == 200:
        print("✅ Tracking Success")
    else:
        print(f"❌ Tracking Failed: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    run_test()
