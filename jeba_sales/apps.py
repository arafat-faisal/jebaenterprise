from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class JebaSalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jeba_sales'
    verbose_name = _("Sales & E-commerce") 

    def ready(self):
        # Import signals handler to ensure they are connected
        import jeba_sales.signals # noqa