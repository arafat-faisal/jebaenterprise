from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
import uuid
from decimal import Decimal

# Import Product from the OTHER app
from jeba_inventory.models import Product, ProductVariation

class Sale(models.Model):
    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('PROCESSING', _('Processing')),
        ('SHIPPED', _('Shipped')),
        ('DELIVERED', _('Delivered')),
        ('CANCELLED', _('Cancelled')),
        ('RETURNED', _('Returned')), # Added RETURNED for better analytics
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

    # NEW FIELDS: These are editable and will hold the manual value.
    manual_subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, 
        verbose_name=_("Subtotal Override"),
        help_text=_("Manually set the subtotal. Leave blank to use sum of items.")
    )
    manual_total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, 
        verbose_name=_("Total Amount Override"),
        help_text=_("Manually set the final total. Leave blank to use Subtotal + Delivery Charge.")
    )

    class Meta:
        db_table = 'products_sale'
        ordering = ['-created_at']

    def __str__(self):
        return f"Sale #{self.id} - {self.status}"

    @property
    def invoice_number(self):
        # FIX: Check if ID exists (is not None)
        if self.id is None:
            return "NEW"
        return f"JEBA-{self.id + 8000}"
    
    @property
    def order_id(self):
        # FIX: Check if ID exists (is not None)
        if self.id is None:
            return "New Order"
        return f"#{self.id + 8000}"
    
    # RENAME: Internal method to calculate the subtotal from line items (always reliable source)
    @property
    def _calculated_subtotal(self):
        return sum(item.total_price for item in self.items.all()) 
    
    # RENAME: Internal method to calculate the total amount from line items + delivery charge
    @property
    def _calculated_total_amount(self):
        return self._calculated_subtotal + self.delivery_charge

    # PUBLIC ACCESSOR: Subtotal (PRIORITIZES editable field if available, else calculates)
    @property
    def subtotal(self):
        return self.manual_subtotal if self.manual_subtotal is not None else self._calculated_subtotal

    # PUBLIC ACCESSOR: Total Amount (PRIORITIZES editable field if available, else calculates)
    @property
    def total_amount(self):
        return self.manual_total_amount if self.manual_total_amount is not None else self._calculated_total_amount

    @property
    def total_profit(self):
        items = self.items.all()
        return sum(item.profit for item in items)


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variation = models.ForeignKey(ProductVariation, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))
    
    # CRITICAL: These record the financial state AT THE TIME OF SALE
    buying_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sold_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Sold Price"))

    class Meta:
        db_table = 'products_saleitem'

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    @property
    def total_price(self):
        price = self.sold_price if self.sold_price is not None else Decimal(0)
        return price * self.quantity

    @property
    def profit(self):
        sold = self.sold_price if self.sold_price is not None else Decimal(0)
        cost = self.buying_cost if self.buying_cost is not None else Decimal(0)
        return (sold - cost) * self.quantity

    def save(self, *args, **kwargs):
        # 1. Capture Buying Cost from Product (or Variation) if not set
        if self.buying_cost == 0:
            if self.product.buying_cost:
                self.buying_cost = self.product.buying_cost
        
        # 2. Capture Sold Price from Product (or Variation) if not set
        if self.sold_price is None or self.sold_price == 0:
            if self.variation and self.variation.selling_price > 0:
                self.sold_price = self.variation.selling_price
            else:
                self.sold_price = self.product.selling_price

        # 3. Handle Stock Deduction (Only on creation)
        if not self.pk: 
            if self.variation:
                self.variation.stock_quantity -= self.quantity
                self.variation.save()
            
            # Reduce parent product stock as well
            self.product.stock_quantity -= self.quantity
            self.product.save()
            
        super().save(*args, **kwargs)

# --- NEW: COUPON MODEL ---
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, help_text="Case insensitive (e.g. SALE10)")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Flat discount amount in Taka")
    min_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Minimum cart total required")
    active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.code