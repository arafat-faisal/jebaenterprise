import json
import time
import random
import uuid
import threading
import requests
from django.core.management.base import BaseCommand

# --- CONFIGURATION ---
# IMPORTANT: Ensure this matches your running Waitress port (8000 or 8080)
TARGET_URL = 'http://127.0.0.1:8080/analytics/ingest-beacon/'

# --- ADVANCED PROFILES ---
DEVICE_TYPES = ['mobile', 'desktop', 'tablet']

DEVICE_PROFILES = {
    'desktop': {
        'weight': 0.3,
        'perf_factor': 0.8, # Faster
        'screen': [1920, 1440, 1366],
        'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    },
    'mobile': {
        'weight': 0.4, # More mobile traffic
        'perf_factor': 2.5, # Slower
        'screen': [390, 375, 428],
        'ua': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    },
    'tablet': {
        'weight': 0.3,
        'perf_factor': 1.5,
        'screen': [768, 810],
        'ua': 'Mozilla/5.0 (iPad; CPU OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1'
    }
}

NETWORK_CONDITIONS = {
    'WIFI_5G': {'weight': 0.5, 'latency': 0.05, 'speed_factor': 1.0},
    '4G_LTE': {'weight': 0.3, 'latency': 0.15, 'speed_factor': 1.5},
    '3G_SLOW': {'weight': 0.2, 'latency': 0.5, 'speed_factor': 3.0},
}

class Command(BaseCommand):
    help = '🚀 Launches a swarm of realistic fake users to stress-test the Analytics Beacon'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=200, help='Number of users to simulate')
        parser.add_argument('--concurrency', type=int, default=20, help='Number of threads')

    def handle(self, *args, **options):
        total_users = options['users']
        concurrency = options['concurrency']
        
        self.stdout.write(self.style.WARNING(f"🔥 INITIATING REALISTIC TEST: {total_users} users targeting {TARGET_URL}"))
        
        start_time = time.time()
        threads = []
        batch_size = total_users // concurrency
        
        for i in range(concurrency):
            count = batch_size + (total_users % concurrency) if i == concurrency - 1 else batch_size
            t = threading.Thread(target=self.simulate_user_batch, args=(count, i))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        duration = time.time() - start_time
        rps = total_users / duration
        self.stdout.write(self.style.SUCCESS(f"✅ MISSION COMPLETE. {total_users} sessions in {duration:.2f}s ({rps:.1f} req/s)"))

    def get_weighted_choice(self, choices):
        total = sum(item['weight'] for item in choices.values())
        r = random.uniform(0, total)
        uptime = 0
        for name, data in choices.items():
            if uptime + data['weight'] >= r:
                return name, data
            uptime += data['weight']
        return list(choices.keys())[0], list(choices.values())[0]

    def simulate_user_batch(self, count, thread_id):
        for i in range(count):
            session_id = str(uuid.uuid4())
            
            # 1. Pick Device Type explicitly
            dtype_key = random.choice(DEVICE_TYPES) # mobile, desktop, tablet
            device = DEVICE_PROFILES[dtype_key]
            
            net_name, network = self.get_weighted_choice(NETWORK_CONDITIONS)
            
            # 2. Calculate Load Time
            total_drag = device['perf_factor'] * network['speed_factor']
            
            ttfb = int(random.uniform(20, 100) * network['speed_factor'])
            dom_ready = int(random.uniform(300, 800) * total_drag)
            full_load = int(dom_ready + random.uniform(100, 1000) * total_drag)
            
            is_bouncer = random.choice([True, False])
            
            behavior_data = {
                'duration': random.randint(50, 800) if is_bouncer else random.randint(5000, 120000),
                'max_scroll': random.randint(0, 20) if is_bouncer else random.randint(50, 100),
                'is_bounce': is_bouncer,
                'performance': {
                    'ttfb': ttfb,
                    'fullLoad': full_load,
                    'domReady': dom_ready
                },
                'screen_width': random.choice(device['screen']),
                'interactions': []
            }

            # 3. Fire Beacon with SPOOFED HEADERS
            payload = {
                'session_id': session_id,
                'url': f'/landing/demo-product?utm_source={net_name}&device={dtype_key}',
                'data': json.dumps(behavior_data)
            }
            
            # --- THE FIX IS HERE ---
            headers = {
                'User-Agent': device['ua']  # <--- CRITICAL: Send the fake UA in the header
            }
            
            try:
                time.sleep(0.01) 
                requests.post(TARGET_URL, data=payload, headers=headers, timeout=10)
            except Exception as e:
                print(f"[{thread_id}] 💥 Failed: {str(e)}")