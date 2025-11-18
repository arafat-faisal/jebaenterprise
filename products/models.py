from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- Category Model ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

# --- Product Model ---
class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    # Added featured field
    is_featured = models.BooleanField(default=False, help_text="Check this to show on Homepage Hero section")

    buying_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock_quantity = models.PositiveIntegerField(default=0)
    box_quantity = models.PositiveIntegerField(default=1, help_text="How many products are in a box")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# --- Product Variation ---
class ProductVariation(models.Model):
    product = models.ForeignKey(Product, related_name='variations', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.name}"
    
# --- Sale Model ---
class Sale(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    shipping_address = models.TextField(blank=True, null=True)
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale #{self.id} - {self.status}"

    @property
    def total_amount(self):
        # Sum of (Sold Price * Quantity) for all items in this sale
        return sum(item.sold_price * item.quantity for item in self.items.all())

    @property
    def total_profit(self):
        items = self.items.all()
        return sum(item.profit for item in items)

# --- Sale Item ---
class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variation = models.ForeignKey(ProductVariation, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    buying_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sold_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    @property
    def profit(self):
        return (self.sold_price - self.buying_cost) * self.quantity

    def save(self, *args, **kwargs):
        if not self.pk: 
            if self.variation:
                self.variation.stock_quantity -= self.quantity
                self.variation.save()
            self.product.stock_quantity -= self.quantity
            self.product.save()
        super().save(*args, **kwargs)

# --- Product Image (Gallery) ---
class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/')
    
    # We keep this field for MANUAL uploads
    transparent_image = models.ImageField(upload_to='products/transparent/', blank=True, null=True, help_text="Upload a PNG with no background here (Optional)")
    
    def __str__(self):
        return f"Image for {self.product.name}"

# --- Competitor Price ---
class CompetitorPrice(models.Model):
    product = models.ForeignKey(Product, related_name='competitor_prices', on_delete=models.CASCADE)
    website_name = models.CharField(max_length=100)
    min_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_checked = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.website_name} price for {self.product.name}"

# --- Reviews ---
class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}*)"

# --- Wishlist ---
class Wishlist(models.Model):
    user = models.ForeignKey(User, related_name='wishlist', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

# --- User Profile ---
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Profile for {self.user.username}"

# --- SAFE SIGNALS (No AI) ---
@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, **kwargs):
    # Safer method to get or create profile
    UserProfile.objects.get_or_create(user=instance)