from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import uuid

# Import Product from the OTHER app
from jeba_inventory.models import Product, ProductVariation

class Sale(models.Model):
    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('PROCESSING', _('Processing')),
        ('SHIPPED', _('Shipped')),
        ('DELIVERED', _('Delivered')),
        ('CANCELLED', _('Cancelled')),
    ]
    PAYMENT_METHODS = [
        ('COD', _('Cash on Delivery')),
        ('BKASH', _('bKash')),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Customer Name"))
    access_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("Phone Number"))
    shipping_address = models.TextField(blank=True, null=True, verbose_name=_("Shipping Address"))
    
    # Steadfast Fields
    consignment_id = models.IntegerField(null=True, blank=True, help_text=_("Steadfast Consignment ID"))
    tracking_code = models.CharField(max_length=50, null=True, blank=True, help_text=_("Steadfast Tracking Code"))

    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='COD', verbose_name=_("Payment Method"))
    transaction_id = models.CharField(max_length=50, blank=True, null=True, verbose_name=_("Transaction ID"))
    delivery_charge = models.DecimalField(max_digits=6, decimal_places=2, default=60.00, verbose_name=_("Delivery Charge"))

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name=_("Status"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'products_sale'

    def __str__(self):
        return f"Sale #{self.id} - {self.status}"

    @property
    def invoice_number(self):
        return f"JEBA-{self.id + 8000}"
    
    @property
    def order_id(self):
        return f"#{self.id + 8000}"
    
    @property
    def total_amount(self):
        item_total = sum(item.sold_price * item.quantity for item in self.items.all())
        return item_total + self.delivery_charge
    
    @property
    def subtotal(self):
        return sum(item.sold_price * item.quantity for item in self.items.all())

    @property
    def total_profit(self):
        items = self.items.all()
        return sum(item.profit for item in items)


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variation = models.ForeignKey(ProductVariation, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))
    buying_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sold_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Sold Price"))

    class Meta:
        db_table = 'products_saleitem'

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    @property
    def profit(self):
        return (self.sold_price - self.buying_cost) * self.quantity

    def save(self, *args, **kwargs):
        # NOTE: Logic to deduct stock should be moved to a Service or Signals. 
        # But keeping it here for now to ensure continuity.
        if not self.pk: 
            if self.variation:
                self.variation.stock_quantity -= self.quantity
                self.variation.save()
            self.product.stock_quantity -= self.quantity
            self.product.save()
        super().save(*args, **kwargs)