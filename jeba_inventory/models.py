from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify

# --- NEW: Tag Model (Fixed Slug Generation) ---
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
        # Only generate slug if it's missing
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            
            # Loop to find a unique slug: "health" -> "health-1" -> "health-2"
            while Tag.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
            
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

    # ==================================================
    # NEW SEO FIELDS (For AI Integration)
    # ==================================================
    meta_title = models.CharField(max_length=255, blank=True, null=True, help_text=_("Manual override for SEO Title"))
    meta_description = models.TextField(blank=True, null=True, help_text=_("Manual override for SEO Description"))
    
    # AI Storage Fields
    meta_title_ai = models.CharField(max_length=255, blank=True, null=True, editable=False)
    meta_description_ai = models.TextField(blank=True, null=True, editable=False)
    is_seo_optimized = models.BooleanField(default=False, help_text=_("True if AI has processed this."))
    # ==================================================

    # --- AI Content Management ---
    # 1. The Suggestion Fields (Where AI stores its ideas)
    ai_suggested_name = models.CharField(
        max_length=255, blank=True, null=True, 
        help_text=_("AI generated product name based on image & attributes.")
    )
    ai_suggested_short_description = models.TextField(blank=True, null=True, help_text="AI generated summary (HTML allowed).")
    ai_suggested_description = models.TextField(
        blank=True, null=True, 
        help_text=_("AI generated description tailored for Bangladeshi audience.")
    )

    # --- NEW: AI Categorization & Tagging ---
    ai_suggested_category = models.CharField(
        max_length=100, blank=True, null=True,
        help_text=_("AI suggested category name. Admin must approve to apply.")
    )
    ai_suggested_tags = models.TextField(
        blank=True, null=True,
        help_text=_("Comma-separated list of AI suggested tags (e.g. 'Summer, Cotton, Sale').")
    )
    # ----------------------------------------

    # 2. The Toggles (You control what the customer sees)
    use_ai_name = models.BooleanField(
        default=False, 
        verbose_name=_("Use AI Name on Frontend"),
        help_text=_("If checked, the website will show 'AI Suggested Name' instead of the manual 'Name'.")
    )
    use_ai_short_description = models.BooleanField(default=False, verbose_name="Use AI Short Desc")
    use_ai_description = models.BooleanField(
        default=False, 
        verbose_name=_("Use AI Description on Frontend"),
        help_text=_("If checked, the website will show 'AI Suggested Description' instead of the manual 'Description'.")
    )

    # 3. Helper Properties (For easy template usage)
    @property
    def display_name(self):
        """Returns AI Name if toggle is ON and AI Name exists; otherwise returns manual Name."""
        if self.use_ai_name and self.ai_suggested_name:
            return self.ai_suggested_name
        return self.name
    @property
    def display_short_description(self):
        # NEW: Logic for Short Description
        if self.use_ai_short_description and self.ai_suggested_short_description:
            return self.ai_suggested_short_description
        return self.short_description
    @property
    def display_description(self):
        """Returns AI Description if toggle is ON and AI exists; otherwise returns manual Description."""
        if self.use_ai_description and self.ai_suggested_description:
            return self.ai_suggested_description
        return self.description

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

    # --- NEW: Variation Logic Helper ---
    @property
    def has_variations(self):
        """Returns True if the product has active variations."""
        return self.variations.filter(is_active=True).exists()
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

# --- Product Variation (UPGRADED) ---
class ProductVariation(models.Model):
    product = models.ForeignKey(Product, related_name='variations', on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name=_("Variation Name"), help_text=_("e.g. Size: XL, Color: Red"))
    
    # Pricing (Upgraded to support discounts per variation)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Selling Price"))
    original_price = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True, 
        verbose_name=_("Original Price"),
        help_text=_("Set higher than selling price to show discount for this specific variation.")
    )
    
    # Inventory (Upgraded)
    sku = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name=_("SKU"))
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name=_("Stock Quantity"))
    
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    class Meta:
        db_table = 'products_productvariation'
        verbose_name = _("Variation")
        verbose_name_plural = _("Variations")

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    # NEW: Properties to handle variation discounts
    @property
    def has_discount(self):
        return self.original_price and self.original_price > self.selling_price

    @property
    def discount_amount(self):
        if self.has_discount:
            return int(self.original_price - self.selling_price)
        return 0

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