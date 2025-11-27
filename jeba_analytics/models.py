from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from jeba_inventory.models import Product

# --- EVENT TRACKING ---
class SearchEvent(models.Model):
    query = models.CharField(max_length=255, verbose_name=_("Search Query"))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Stores IP, Location, Device Info
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Event Metadata"))
    
    # NEW: Store result count explicitly for "Zero Result" analysis
    result_count = models.PositiveIntegerField(default=0, verbose_name=_("Results Found"))
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'products_searchevent' # Keep legacy table name for safety
        verbose_name = _("Search Log")
        verbose_name_plural = _("Search Logs")

    def __str__(self):
        return f"Search: {self.query} ({self.result_count})"
    
class ProductEvent(models.Model):
    EVENT_CHOICES = [
        ('VIEW', _('Product View')),
        ('CART', _('Added to Cart')),
        ('PURCHASE', _('Purchased')),
        ('SHARE', _('Shared')),
        ('CONTACT', _('Contact Click')), 
        ('CHECKOUT', _('Initiated Checkout')),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='events')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    
    # NEW: Capture price at the time of event (Crucial for historic Cart Value analysis)
    value_at_event = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text=_("Product selling price at the moment of this event.")
    )

    # Stores Source (FB/Google), Campaign ID, etc.
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Product Interaction")
        db_table = 'products_productevent' # Keep legacy table name

    def __str__(self):
        return f"{self.product.name} - {self.event_type}"

    def save(self, *args, **kwargs):
        # Auto-fill value from product if not set
        if self.value_at_event is None and self.product:
            self.value_at_event = self.product.selling_price
        super().save(*args, **kwargs)


# --- NEW: PROFIT & ROI ANALYTICS ---
class DailyAdSpend(models.Model):
    """
    Tracks daily marketing costs to calculate ROI and Net Profit.
    """
    date = models.DateField(unique=True, verbose_name=_("Spend Date"))
    
    # Platform breakdown
    facebook_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("Facebook Ads (Tk)"))
    google_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("Google Ads (Tk)"))
    tiktok_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("TikTok/Other (Tk)"))
    
    # Store aggregated stats for that day (Caching for performance)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, editable=False)
    total_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, editable=False)
    total_orders = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        db_table = 'jeba_analytics_adspend'
        verbose_name = _("Daily Marketing & ROI")
        verbose_name_plural = _("Daily Marketing & ROI")
        ordering = ['-date']

    def __str__(self):
        return f"{self.date}: {self.total_spend} Tk Spend"

    @property
    def total_spend(self):
        return self.facebook_spend + self.google_spend + self.tiktok_spend

    @property
    def net_profit(self):
        """Gross Profit from Sales - Ad Spend"""
        return self.total_profit - self.total_spend

    @property
    def roas(self):
        """Return on Ad Spend (Revenue / Spend)"""
        if self.total_spend > 0:
            return round(self.total_revenue / self.total_spend, 2)
        return 0.0