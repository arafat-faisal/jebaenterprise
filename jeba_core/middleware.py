from django.shortcuts import redirect, render
from django.conf import settings
from jeba_core.models import SiteSettings

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        settings_obj = SiteSettings.load()
        
        # Check if maintenance mode is enabled and user is not superuser and not accessing admin
        if settings_obj.maintenance_mode and not request.path.startswith('/admin') and not (request.user.is_authenticated and request.user.is_superuser):
            
            # Allow access to static/media files
            if not (request.path.startswith(settings.STATIC_URL) or request.path.startswith(settings.MEDIA_URL)):
                # Allow access to the login page if not logged in
                if request.path != '/accounts/login/':
                    return render(request, 'jeba_core/maintenance.html', status=503)

        response = self.get_response(request)
        return response