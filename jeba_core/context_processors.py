from jeba_core.models import SiteSettings

def global_settings(request):
    """
    Makes site-wide settings available in EVERY template.
    Refactored from products app to jeba_core.
    """
    return {
        'site_settings': SiteSettings.load()
    }