from .models import SiteSettings

def global_settings(request):
    # This makes {{ site_settings }} available in EVERY template
    return {
        'site_settings': SiteSettings.load()
    }