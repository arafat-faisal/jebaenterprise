from django.shortcuts import render
from django.conf import settings
from .models import SiteSettings  # <--- Import the model to check the DB

class MaintenanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Allow access to Admin panel even in maintenance mode
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        # 2. Allow access to static and media files 
        # (Ensures styles/images load on the maintenance page)
        static_url = getattr(settings, 'STATIC_URL', '/static/')
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        
        if request.path.startswith(static_url) or request.path.startswith(media_url):
            return self.get_response(request)

        # 3. Check Database Toggle (The Admin Checkbox)
        try:
            # Load the settings object from the DB
            config = SiteSettings.load()
            if config.maintenance_mode:
                return render(request, 'maintenance.html', status=503)
        except Exception:
            # If the table doesn't exist yet (e.g. during migrations), ignore
            pass

        # 4. Fallback to settings.py (Optional override from .env)
        if getattr(settings, 'MAINTENANCE_MODE', False):
            return render(request, 'maintenance.html', status=503)

        # 5. Otherwise, proceed as normal
        return self.get_response(request)