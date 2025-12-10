🚀 PHASE 5: PRODUCTION LAUNCH PROTOCOL
1. The "Waitress" Mandate
NEVER use manage.py runserver in production. It will choke and die under ad traffic.

Windows Server: Continue using waitress.

PowerShell

waitress-serve --listen=0.0.0.0:8000 config.wsgi:application
Linux (DigitalOcean/AWS): Use Gunicorn + Nginx.

Bash

gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
2. Database Optimization (The Bottleneck)
Your SessionTrace table will grow very fast (100k+ rows/month if you spend money).

Index Check: I already added db_index=True to session_id in models.py. We are good.

Cleanup Routine: You don't need analytics from 2 years ago.

Recommendation: Set up a cron job (monthly) to delete records older than 90 days if your DB gets too big.

3. Static Files (The Probe)
Ensure you run:

Bash

python manage.py collectstatic
Verify: Check that landing_analytics.js is actually in your staticfiles folder and being served. If this 404s, you are flying blind.

4. Security & CORS
HTTPS is Mandatory: navigator.sendBeacon and modern browser security features require HTTPS to work reliably.

If you deploy on HTTP (Unsecured), 30-40% of your data will be blocked by Chrome/iOS.

CORS (Cross-Origin Resource Sharing):

If your landing page is on shop.jeba.com but your admin is admin.jeba.com, the beacon will fail unless you install django-cors-headers.

Current Setup: Since you are likely serving everything from the same domain, you are safe.

5. "Warm Up" The Cache
The first time you load that Admin Dashboard with 50,000 records, it might take 2 seconds to calculate the charts.

Django's database caching will help subsequent loads.