# --- MODULAR IMPORT ---
from jeba_core.models import SiteSettings
# ----------------------

def global_settings(request):
    """
    Makes site-wide settings available in EVERY template.
    """
    # Load the singleton object (creates it if missing)
    return {
        'site_settings': SiteSettings.load()
    }