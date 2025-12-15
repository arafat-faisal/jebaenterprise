import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def analyze_page_performance(target_url, request=None):
    """
    Analyzes a given URL for performance bottlenecks.
    Note: This runs on the SERVER side, so 'response time' is server-to-server or localhost.
    It simulates what the browser receives initially.
    """
    report = {
        'url': target_url,
        'ttfb': 0,
        'total_time': 0,
        'html_size': 0,
        'images': [],
        'scripts': [],
        'css': [],
        'suggestions': [],
        'score': 100
    }
    
    # 1. Measure Server Response (HTML)
    try:
        start_time = time.time()
        # Use a session to persist cookies if needed, or simple get
        # If target_url is relative, make it absolute using localhost
        if target_url.startswith('/'):
            # Determine host. If request is provided, use it.
            if request:
                scheme = request.scheme
                host = request.get_host()
                target_url = f"{scheme}://{host}{target_url}"
            else:
                target_url = f"http://127.0.0.1:8000{target_url}" # Fallback
                
        resp = requests.get(target_url, timeout=10)
        end_time = time.time()
        
        report['url'] = target_url
        report['total_time'] = int((end_time - start_time) * 1000)
        report['ttfb'] = int(resp.elapsed.total_seconds() * 1000) # Roughly TTFB
        report['html_size'] = len(resp.content)
        
        if resp.status_code != 200:
            report['suggestions'].append(f"Page returned status code {resp.status_code}")
            report['score'] -= 20
            return report

    except Exception as e:
        report['suggestions'].append(f"Failed to fetch page: {str(e)}")
        report['score'] = 0
        return report

    # 2. Parse HTML
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    # 3. Analyze Images
    imgs = soup.find_all('img')
    total_img_size = 0
    large_images = 0
    
    for img in imgs:
        src = img.get('src')
        if not src:
            continue
            
        # Resolve URL
        if src.startswith('data:'):
            # Data URI
            size = len(src)
            name = "Data URI (embedded)"
            is_external = False
        else:
            full_src = urljoin(target_url, src)
            name = src.split('/')[-1] or src
            size = 0
            is_external = True
            
            # Try to get size via HEAD request
            # Optimization: Try locally if it's media?
            # For now, let's just requests.head
            try:
                head = requests.head(full_src, timeout=2)
                if 'Content-Length' in head.headers:
                    size = int(head.headers['Content-Length'])
            except:
                pass
        
        img_info = {
            'src': src,
            'name': name,
            'size': size,
            'display_size': f"{size/1024:.1f} KB" if size else "Unknown"
        }
        
        # Heuristics
        if size > 200 * 1024: # > 200KB
            img_info['warning'] = 'Large Image (>200KB)'
            large_images += 1
            report['score'] -= 5
        
        # Check for width/height attributes (CLS)
        if not img.get('width') or not img.get('height'):
            img_info['cls_warning'] = 'Missing width/height attributes (CLS risk)'
            report['score'] -= 1
            
        report['images'].append(img_info)
        total_img_size += size

    if large_images > 0:
        report['suggestions'].append(f"Found {large_images} images larger than 200KB. Compress them or use WebP.")
        
    # 4. Analyze Scripts
    scripts = soup.find_all('script', src=True)
    report['script_count'] = len(scripts)
    for s in scripts:
        src = s.get('src')
        info = {'src': src, 'defer': s.get('defer') is not None, 'async': s.get('async') is not None}
        
        if not info['defer'] and not info['async'] and 'cdn.tailwindcss.com' not in src:
             # Heuristic: Blocking script?
             # Ignoring Tailwind CDN as user explicitly added it.
             report['suggestions'].append(f"Blocking script found: {src.split('/')[-1]}. Consider adding 'defer'.")
             report['score'] -= 5
             
        report['scripts'].append(info)

    # 5. Summarize
    report['total_assets_size'] = report['html_size'] + total_img_size
    
    # Simple Grading
    if report['total_time'] > 1000: # > 1s server time
        report['suggestions'].append("Server response is slow (>1s). Check database queries or view logic.")
        report['score'] -= 20
    elif report['total_time'] > 500:
        report['suggestions'].append("Server response could be faster (>500ms).")
        report['score'] -= 10
        
    report['score'] = max(0, report['score']) # Min 0
    
    return report
