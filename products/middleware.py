from django.shortcuts import render, redirect
from django.urls import reverse
# --- MODULAR IMPORT FIX ---
from jeba_core.models import SiteSettings
# --------------------------

class MaintenanceModeMiddleware:
    """
    Middleware to check if the site is in maintenance mode.
    Allows access to Admin and Login pages.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Paths to ignore (always accessible)
        path = request.path_info
        if path.startswith(reverse('admin:index')) or path.startswith('/admin/') or path.startswith('/accounts/login/'):
            return self.get_response(request)

        # Check Global Settings
        try:
            settings_obj = SiteSettings.load()
            if settings_obj.maintenance_mode:
                # If user is staff, allow access
                if request.user.is_authenticated and request.user.is_staff:
                    return self.get_response(request)
                
                # Otherwise, show Maintenance Page
                return render(request, 'maintenance.html')
        except Exception:
            # If table doesn't exist yet (during migrations), skip logic
            pass

        return self.get_response(request)