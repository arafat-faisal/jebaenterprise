from django.db import models
from django.utils.translation import gettext_lazy as _
from jeba_inventory.models import Product

class CompetitorPrice(models.Model):
    product = models.ForeignKey(Product, related_name='competitor_prices', on_delete=models.CASCADE)
    website_name = models.CharField(max_length=100, verbose_name=_("Website Name"))
    min_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_checked = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products_competitorprice'

    def __str__(self):
        return f"{self.website_name} price for {self.product.name}"

class ScraperPreset(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Preset Name"))
    image_weight = models.DecimalField(max_digits=3, decimal_places=2, default=0.3)
    text_weight = models.DecimalField(max_digits=3, decimal_places=2, default=0.7)
    confidence_threshold = models.IntegerField(default=60)
    text_slam_dunk = models.IntegerField(default=85)
    image_slam_dunk = models.IntegerField(default=90)

    class Meta:
        db_table = 'products_scraperpreset'

    def __str__(self):
        return self.name