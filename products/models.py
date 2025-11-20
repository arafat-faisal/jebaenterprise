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
    short_description = models.TextField(blank=True, null=True, help_text="Short summary shown beside the image")

    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    call_for_price = models.BooleanField(default=False, help_text="If checked, price will be hidden and 'Call for Price' shown.")
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
    @property
    def main_image_obj(self):
        """Returns the ProductImage object that is main, or the first one as fallback."""
        # 1. Try to get the image marked as "Main"
        main = self.images.filter(is_main=True).first()
        if main:
            return main
        # 2. Fallback
        return self.images.first()

    @property
    def thumbnail(self):
        """Returns the image file of the main image."""
        img_obj = self.main_image_obj
        return img_obj.image if img_obj else None

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
    
    # --- NEW STEADFAST FIELDS ---
    consignment_id = models.IntegerField(null=True, blank=True, help_text="Steadfast Consignment ID")
    tracking_code = models.CharField(max_length=50, null=True, blank=True, help_text="Steadfast Tracking Code")
    # ----------------------------

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    # --- NEW FIELDS ---
    PAYMENT_METHODS = [
        ('COD', 'Cash on Delivery'),
        ('BKASH', 'bKash'),
    ]
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='COD')
    transaction_id = models.CharField(max_length=50, blank=True, null=True)
    # ------------------

    # --- NEW FIELD ---
    delivery_charge = models.DecimalField(max_digits=6, decimal_places=2, default=60.00)
    # -----------------

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale #{self.id} - {self.status}"

    # --- ADD THIS NEW PROPERTY ---
    @property
    def invoice_number(self):
        return f"JEBA-{self.id + 8000}"
    
    @property
    def order_id(self):
        # This turns ID 49 into "8049" and ID 100 into "8100"
        # It looks professional but keeps your database simple.
        return f"#{self.id + 8000}"
    
    @property
    def total_amount(self):
        item_total = sum(item.sold_price * item.quantity for item in self.items.all())
        return item_total + self.delivery_charge
    

    # --- ADD THIS NEW PROPERTY ---
    @property
    def subtotal(self):
        return sum(item.sold_price * item.quantity for item in self.items.all())
    # -----------------------------

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
    is_main = models.BooleanField(default=False, verbose_name="Main Thumbnail")

    def save(self, *args, **kwargs):
        # Ensure only one image is marked as main per product
        if self.is_main:
            ProductImage.objects.filter(product=self.product).exclude(id=self.id).update(is_main=False)
        super().save(*args, **kwargs)

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


# ... existing code ...

# --- GLOBAL SITE SETTINGS ---
class SiteSettings(models.Model):
    """
    Singleton model to store global configuration.
    Only one instance of this should ever exist.
    """
    bkash_number = models.CharField(max_length=15, default="017XXXXXXXX", help_text="Personal bKash Number for manual payments")
    delivery_charge_inside = models.DecimalField(max_digits=5, decimal_places=0, default=60, help_text="Delivery charge inside Dhaka")
    delivery_charge_outside = models.DecimalField(max_digits=5, decimal_places=0, default=120, help_text="Delivery charge outside Dhaka")

    # --- NEW SOCIAL FIELDS ---
    facebook_page_url = models.URLField(blank=True, null=True, default="https://facebook.com", help_text="Full URL to your Facebook Page")
    messenger_username = models.CharField(max_length=50, blank=True, null=True, help_text="Your Page Username or ID (e.g. 'JebaEnterprise')")
    # -------------------------

    # --- NEW FIELD ---
    meta_pixel_id = models.CharField(max_length=50, blank=True, null=True, help_text="Your Meta Pixel ID (e.g. '1234567890')")
    # -----------------
    # NEW FIELD FOR CAPI
    meta_access_token = models.TextField(blank=True, null=True, help_text="Long Access Token from Events Manager > Settings > Conversions API")
    # -----------------------------

    # --- NEW CONTACT FIELDS ---
    contact_phone = models.CharField(max_length=20, default="+880 1771-000000", help_text="Support Phone Number")
    contact_email = models.EmailField(default="jebaenterprisebd@gmail.com", help_text="Support Email")
    contact_address = models.TextField(default="H# 00/00, AAAAA, AAAAA, AAAA", help_text="Physical Office Address")
    business_hours = models.CharField(max_length=100, default="Sat - Thu: 10:00 AM - 8:00 PM", help_text="e.g. Sat-Thu 10am-8pm")
    # --------------------------

    # --- NEW WHATSAPP FIELDS ---
    whatsapp_number = models.CharField(max_length=20, default="8801716330967", help_text="WhatsApp number for direct contact (Start with country code, e.g., 88017...).")
    contact_message_template = models.TextField(
        default="আমি [PRODUCT_NAME] সম্পর্কে বিস্তারিত তথ্য জানতে আগ্রহী। প্রোডাক্ট লিংক: [PRODUCT_LINK]", 
        help_text="Bengali message template. Use [PRODUCT_NAME] and [PRODUCT_LINK] placeholders."
    )
    # ---------------------------
    
    call_for_price = models.BooleanField(default=False, help_text="If checked, price will be hidden and 'Contact for Price' shown.")

    def save(self, *args, **kwargs):
        # Force ID to be 1 so there's only ever one settings object
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Prevent deletion
        pass

    @classmethod
    def load(cls):
        """
        Helper to get the settings object (creates it if missing).
        """
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    class Meta:
        verbose_name_plural = "Site Settings"