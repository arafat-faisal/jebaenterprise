from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from jeba_inventory.models import Product

class SearchEvent(models.Model):
    query = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'products_searchevent'

    def __str__(self):
        return f"Search: {self.query}"
    
class ProductEvent(models.Model):
    EVENT_CHOICES = [
        ('VIEW', _('Product View')),
        ('CART', _('Added to Cart')),
        ('PURCHASE', _('Purchased')),
        ('SHARE', _('Shared')),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='events')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'products_productevent'

    def __str__(self):
        return f"{self.product.name} - {self.event_type}"