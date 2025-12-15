from django.db import models
from django.utils.translation import gettext_lazy as _

class SiteSettings(models.Model):
    """
    Singleton model to store global configuration.
    """
    # --- HERO SECTION CONTROL ---
    featured_products = models.ManyToManyField(
        'jeba_inventory.Product',
        blank=True,
        related_name='featured_in_hero',
        verbose_name=_("Hero Section Products"),
        help_text=_("Select specific products to display in the Homepage Hero Slider. If empty, the system will use products marked 'Is Featured'.")
    )
    # ----------------------------

    # --- BRANDING ---
    logo = models.ImageField(
        upload_to='site/branding/', 
        null=True, 
        blank=True, 
        help_text=_("Main Website Logo")
    )
    favicon = models.ImageField(
        upload_to='site/branding/', 
        null=True, 
        blank=True, 
        help_text=_("Browser Favicon")
    )

    # --- GLOBAL SCRIPTS (SEO/TRACKING) ---
    header_scripts = models.TextField(
        blank=True, 
        null=True, 
        default="",
        help_text=_("Scripts to inject in <head> like Google Analytics, Pixel Base Code, etc.")
    )
    footer_scripts = models.TextField(
        blank=True, 
        null=True, 
        default="", 
        help_text=_("Scripts to inject before </body> like Chat Widgets.")
    )

    bkash_number = models.CharField(
        max_length=15, 
        default="017XXXXXXXX", 
        help_text=_("Personal bKash Number for manual payments")
    )
    delivery_charge_inside = models.DecimalField(
        max_digits=5, 
        decimal_places=0, 
        default=60, 
        help_text=_("Delivery charge inside Dhaka")
    )
    delivery_charge_outside = models.DecimalField(
        max_digits=5, 
        decimal_places=0, 
        default=120, 
        help_text=_("Delivery charge outside Dhaka")
    )

    # Social Fields
    facebook_page_url = models.URLField(
        blank=True, 
        null=True, 
        default="https://facebook.com", 
        help_text=_("Full URL to your Facebook Page")
    )
    messenger_username = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text=_("Your Page Username or ID (e.g. 'JebaEnterprise')")
    )

    # Meta/Pixel
    meta_pixel_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text=_("Your Meta Pixel ID (e.g. '1234567890')")
    )
    meta_access_token = models.TextField(
        blank=True, 
        null=True, 
        help_text=_("Long Access Token from Events Manager > Settings > Conversions API")
    )

    # Contact Fields
    contact_phone = models.CharField(
        max_length=20, 
        default="+880 1771-000000", 
        help_text=_("Support Phone Number")
    )
    contact_email = models.EmailField(
        default="jebaenterprisebd@gmail.com", 
        help_text=_("Support Email")
    )
    contact_address = models.TextField(
        default="H# 00/00, AAAAA, AAAAA, AAAA", 
        help_text=_("Physical Office Address")
    )
    business_hours = models.CharField(
        max_length=100, 
        default="Sat - Thu: 10:00 AM - 8:00 PM", 
        help_text=_("e.g. Sat-Thu 10am-8pm")
    )

    # WhatsApp
    whatsapp_number = models.CharField(
        max_length=20, 
        default="8801716330967", 
        help_text=_("WhatsApp number for direct contact (Start with country code, e.g., 88017...).")
    )
    contact_message_template = models.TextField(
        default="আমি [PRODUCT_NAME] সম্পর্কে বিস্তারিত তথ্য জানতে আগ্রহী। প্রোডাক্ট লিংক: [PRODUCT_LINK]", 
        help_text=_("Bengali message template. Use [PRODUCT_NAME] and [PRODUCT_LINK] placeholders.")
    )
    
    call_for_price = models.BooleanField(
        default=False, 
        help_text=_("If checked, price will be hidden and 'Contact for Price' shown.")
    )

    maintenance_mode = models.BooleanField(
        default=False, 
        help_text=_("If checked, the entire site (except admin) will show the 'Under Maintenance' page.")
    )

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    class Meta:
        verbose_name_plural = _("Site Settings")
        # DATA PRESERVATION: Point to existing table
        db_table = 'products_sitesettings'