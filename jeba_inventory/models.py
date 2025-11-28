from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify

# --- NEW: Tag Model ---
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name=_("Tag Name"))
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    class Meta:
        verbose_name = _("Product Tag")
        verbose_name_plural = _("Product Tags")
        db_table = 'jeba_inventory_tag'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

# --- Category Model ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Name"))

    class Meta:
        verbose_name_plural = _("Categories")
        db_table = 'products_category'

    def __str__(self):
        return self.name

# --- Product Model ---
class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Product Name"))
    short_description = models.TextField(
        blank=True, null=True, 
        help_text=_("Short summary shown beside the image"),
        verbose_name=_("Short Description")
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Full Description"))
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='products',
        verbose_name=_("Category")
    )
    
    # --- NEW: Visibility & SEO ---
    is_active = models.BooleanField(
        default=True, 
        verbose_name=_("Visible in Store"),
        help_text=_("Uncheck to hide this product from the frontend without deleting it.")
    )
    tags = models.ManyToManyField(
        Tag, 
        blank=True, 
        related_name='products',
        verbose_name=_("SEO Tags"),
        help_text=_("Add tags for better search visibility (e.g., 'Summer', 'Gift', 'Office').")
    )
    # -----------------------------

    call_for_price = models.BooleanField(
        default=False, 
        help_text=_("If checked, price will be hidden and 'Call for Price' shown."),
        verbose_name=_("Call for Price")
    )
    is_featured = models.BooleanField(
        default=False, 
        help_text=_("Check this to show on Homepage Hero section"),
        verbose_name=_("Is Featured")
    )

    buying_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("Buying Cost"))
    # --- PRICING & DISCOUNTS ---
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name=_("Selling Price"))
    original_price = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True, 
        verbose_name=_("Original / Market Price"),
        help_text=_("Set this HIGHER than Selling Price to show a discount (e.g. ~~1200~~ 1000).")
    )
    # ---------------------------
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name=_("Stock Quantity"))
    box_quantity = models.PositiveIntegerField(
        default=1, 
        help_text=_("How many products are in a box"),
        verbose_name=_("Box Quantity")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products_product'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.selling_price > 0 and self.call_for_price:
            self.call_for_price = False
        super().save(*args, **kwargs)

    @property
    def main_image_obj(self):
        main = self.images.filter(is_main=True).first()
        if main:
            return main
        return self.images.first()

    @property
    def thumbnail(self):
        img_obj = self.main_image_obj
        return img_obj.image if img_obj else None
    # --- NEW: Discount Logic ---
    @property
    def has_discount(self):
        return self.original_price and self.original_price > self.selling_price

    @property
    def discount_amount(self):
        if self.has_discount:
            return int(self.original_price - self.selling_price)
        return 0
    # ---------------------------
    def auto_assign_category(self):
        CATEGORY_KEYWORDS = {
            'Electronics': ['phone', 'mobile', 'laptop', 'camera', 'earphone', 'headphone', 'charger', 'cable', 'usb', 'speaker', 'watch', 'smart', 'tv', 'gadget', 'wireless', 'bluetooth'],
            'Fashion': ['shirt', 'pant', 't-shirt', 'shoe', 'dress', 'saree', 'panjabi', 'bag', 'wallet', 'belt', 'cloth', 'wear', 'jersey'],
            'Beauty & Health': ['cream', 'oil', 'shampoo', 'soap', 'makeup', 'perfume', 'lipstick', 'face', 'skin', 'hair', 'lotion'],
            'Home & Living': ['bed', 'chair', 'table', 'sofa', 'light', 'lamp', 'decor', 'kitchen', 'bottle', 'mug', 'pillow', 'shelf'],
            'Groceries': ['rice', 'oil', 'dal', 'spice', 'sugar', 'tea', 'coffee', 'food', 'snack', 'chocolate', 'biscuit'],
            'Toys & Games': ['toy', 'doll', 'game', 'car', 'remote', 'puzzle', 'lego', 'teddy'],
            'Automotive': ['bike', 'car', 'helmet', 'engine', 'oil', 'tire', 'parts'],
            'Video & Audio': ['microphone', 'tripod', 'studio', 'vlog', 'kit', 'ring light', 'stand', 'recording'],
        }

        name_lower = self.name.lower()
        found_category_name = None
        
        for cat_name, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name_lower:
                    found_category_name = cat_name
                    break
            if found_category_name:
                break
        
        if found_category_name:
            category_obj, created = Category.objects.get_or_create(name=found_category_name)
            self.category = category_obj
            self.save()
            return True
        return False

    def apply_dynamic_pricing(self):
        from jeba_intelligence.models import CompetitorPrice
        
        comp_prices = self.competitor_prices.all()
        if not comp_prices.exists(): return False 

        valid_prices = [cp.min_price for cp in comp_prices if cp.min_price and cp.min_price > 0]
        if not valid_prices: return False

        avg_min_price = sum(valid_prices) / len(valid_prices)
        new_selling_price = avg_min_price - 50
        
        if self.buying_cost > 0 and new_selling_price < self.buying_cost:
             new_selling_price = self.buying_cost + 10 

        self.selling_price = new_selling_price
        self.save()
        return True

# --- Product Variation ---
class ProductVariation(models.Model):
    product = models.ForeignKey(Product, related_name='variations', on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name=_("Variation Name"))
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Selling Price"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name=_("Stock Quantity"))

    class Meta:
        db_table = 'products_productvariation'

    def __str__(self):
        return f"{self.product.name} - {self.name}"

# --- Product Image ---
class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/', verbose_name=_("Image"))
    transparent_image = models.ImageField(
        upload_to='products/transparent/', 
        blank=True, null=True, 
        help_text=_("Upload a PNG with no background here (Optional)"),
        verbose_name=_("Transparent Image")
    )
    is_main = models.BooleanField(default=False, verbose_name=_("Main Thumbnail"))

    class Meta:
        db_table = 'products_productimage'

    def save(self, *args, **kwargs):
        if self.is_main:
            ProductImage.objects.filter(product=self.product).exclude(id=self.id).update(is_main=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.product.name}"