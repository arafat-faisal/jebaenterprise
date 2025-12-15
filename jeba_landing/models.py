from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.conf import settings
import uuid
import json

# Try to import Product, handle if missing for initial migration steps
try:
    from jeba_inventory.models import Product
except ImportError:
    Product = None

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# --- 1. CAMPAIGN MANAGEMENT ---

class Campaign(TimeStampedModel):
    """
    The umbrella container for a landing page strategy. 
    It can reference a specific Product or just be a general promo.
    """
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    product = models.ForeignKey(
        'jeba_inventory.Product', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='landing_campaigns'
    )
    is_active = models.BooleanField(default=False)
    
    # Meta / SEO
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_pixel_id = models.CharField(max_length=50, blank=True, help_text="Specific Pixel for this campaign (overrides global)")
    
    # AI Automation
    manual_ai_prompt = models.TextField(blank=True, null=True, help_text="Paste AI-generated JSON here to auto-create variants/sections.")
    
    # Localization
    currency = models.CharField(max_length=10, default='BDT', choices=[('BDT', 'Taka'), ('USD', 'USD')])
    language_toggle = models.BooleanField(default=True, help_text="Allow users to switch between BN/EN")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class CampaignVariant(TimeStampedModel):
    """
    A specific version of the campaign for A/B testing.
    e.g. 'Variant A: Video Hero' vs 'Variant B: Static Image'
    """
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100, help_text="e.g. 'Control', 'Video Hero'")
    weight = models.PositiveIntegerField(default=50, help_text="Traffic percentage (0-100)")
    
    # Design Overrides
    primary_color = models.CharField(max_length=20, default="#D4F759")
    accent_color = models.CharField(max_length=20, default="#000000")
    
    # Psychology Triggers
    enable_fomo_timer = models.BooleanField(default=False)
    fomo_timer_end = models.DateTimeField(null=True, blank=True)
    enable_social_proof = models.BooleanField(default=True, help_text="Show 'X people viewing now'")
    enable_exit_popup = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.campaign.slug} - {self.name} ({self.weight}%)"

class LandingSection(models.Model):
    """
    Modular blocks that make up a Variant.
    """
    SECTION_TYPES = [
        ('HERO_CAROUSEL', 'Hero Carousel'),
        ('HERO_VIDEO', 'Hero Video'),
        ('FEATURES', 'Features Grid'),
        ('PRODUCT_HIGHLIGHT', 'Product Highlight (Split)'),
        ('TESTIMONIALS', 'Testimonials'),
        ('FAQ', 'FAQ Accordion'),
        ('CTA_Sticky', 'Sticky Bottom CTA'),
        ('HTML', 'Raw HTML'),
    ]
    
    variant = models.ForeignKey(CampaignVariant, on_delete=models.CASCADE, related_name='sections')
    section_type = models.CharField(max_length=50, choices=SECTION_TYPES)
    order = models.PositiveIntegerField(default=0)
    
    # Content (JSON for flexibility)
    content = models.JSONField(default=dict, blank=True, help_text="JSON structure for the section content")
    
    # Styling
    is_dark_mode = models.BooleanField(default=False)
    padding_y = models.CharField(max_length=20, default="py-12")
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.get_section_type_display()} (Order: {self.order})"

# --- 2. ANALYTICS ENGINE ("THE MONSTER") ---

class VisitorSession(TimeStampedModel):
    """
    Identifies a unique browser/user session.
    """
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='sessions')
    variant = models.ForeignKey(CampaignVariant, on_delete=models.SET_NULL, null=True, related_name='sessions')
    
    session_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=20, default='mobile') # mobile, tablet, desktop
    
    # Geo (from IP)
    country = models.CharField(max_length=50, default='Bangladesh')
    city = models.CharField(max_length=100, blank=True)
    
    # Referral
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    referrer_url = models.TextField(blank=True)

    def __str__(self):
        return str(self.session_uuid)

class ConversionEvent(TimeStampedModel):
    """
    Tracks specific actions: View, Click, Scroll, AddToCart, Purchase
    """
    EVENT_TYPES = [
        ('PAGE_VIEW', 'Page View'),
        ('SCROLL_50', 'Scrolled 50%'),
        ('SCROLL_90', 'Scrolled 90%'),
        ('CLICK_CTA', 'Clicked CTA'),
        ('ADD_TO_CART', 'Added to Cart'),
        ('INITIATE_CHECKOUT', 'Initiated Checkout'),
        ('PURCHASE', 'Purchase Completed'),
        ('EXIT_INTENT', 'Exit Intent Triggered'),
        ('HEARTBEAT', 'Time on Page (Heartbeat)'),
    ]
    
    session = models.ForeignKey(VisitorSession, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    
    # Context
    metadata = models.JSONField(default=dict, blank=True, help_text="Extra data like button text, scroll depth, or product ID")
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Monetary value if applicable")

    class Meta:
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.session}"