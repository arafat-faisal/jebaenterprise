from django.db import models

class GlobalSEOSettings(models.Model):
    """Singleton model to store site-wide defaults."""
    site_name = models.CharField(max_length=100, default="Jeba Enterprise")
    default_meta_title = models.CharField(max_length=60, help_text="Fallback title")
    default_meta_description = models.CharField(max_length=160, help_text="Fallback description")
    
    # Social Media Defaults
    default_social_image = models.ImageField(upload_to='seo/', blank=True, null=True)
    
    # --- NEW: Ownership Verification ---
    google_site_verification = models.CharField(max_length=100, blank=True, help_text="Google Search Console verification code")
    bing_site_verification = models.CharField(max_length=100, blank=True, help_text="Bing Webmaster Tools verification code")
    facebook_domain_verification = models.CharField(max_length=100, blank=True, help_text="Facebook Domain Verification code")
    # -----------------------------------
    
    def __str__(self):
        return "Global SEO Settings"

    class Meta:
        verbose_name = "Global SEO Settings"
        verbose_name_plural = "Global SEO Settings"


class StaticPageSEO(models.Model):
    """
    Manages SEO for static pages (Home, About, Contact, etc.)
    that don't have their own specific DB models.
    """
    PAGE_CHOICES = [
        ('home', 'Home Page'),
        ('about', 'About Us'),
        ('contact', 'Contact Us'),
        ('login', 'Login'),
        ('register', 'Register'),
        # Add more static pages here as needed
    ]
    
    page_name = models.CharField(max_length=50, choices=PAGE_CHOICES, unique=True)
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    
    # AI Fields (New)
    meta_title_ai = models.CharField(max_length=255, blank=True, null=True, editable=False)
    meta_description_ai = models.TextField(blank=True, null=True, editable=False)
    is_seo_optimized = models.BooleanField(default=False, help_text="True if AI has processed this.")
    def __str__(self):
        return dict(self.PAGE_CHOICES).get(self.page_name, self.page_name)