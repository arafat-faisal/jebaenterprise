from django.db import models
from django.utils.translation import gettext_lazy as _

class PageReport(models.Model):
    """
    Stores analysis results for a specific URL.
    """
    url = models.CharField(max_length=500, verbose_name=_("Tested URL"))
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Timing
    total_time_ms = models.IntegerField(help_text="Total response time in ms", default=0)
    ttfb_ms = models.IntegerField(help_text="Time to First Byte in ms", default=0)
    download_time_ms = models.IntegerField(help_text="Content download time in ms", default=0)
    
    # Size
    html_size_bytes = models.IntegerField(default=0)
    total_assets_size_bytes = models.IntegerField(default=0)
    
    # Assets Counts
    image_count = models.IntegerField(default=0)
    script_count = models.IntegerField(default=0)
    css_count = models.IntegerField(default=0)
    
    # Analysis JSON (Detailed breakdown)
    details = models.JSONField(default=dict)
    
    # Score (0-100)
    performance_score = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.url} - {self.total_time_ms}ms ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    class Meta:
        ordering = ['-created_at']
