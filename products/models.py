from django.db import models
from django.contrib.auth.models import User



# --- ADD THIS NEW CLASS ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Categories" # Fixes the plural name in admin

    def __str__(self):
        return self.name

# --- End of Category Model ---

class Product(models.Model):
    # ... all your existing Product fields are here ...
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    # image = models.ImageField(upload_to='products/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')

    buying_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock_quantity = models.PositiveIntegerField(default=0)
    box_quantity = models.PositiveIntegerField(default=1, help_text="How many products are in a box")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# --- ADD THIS NEW CLASS ---
class ProductVariation(models.Model):
    # This is the "link" to the main product
    # models.CASCADE means if you delete a product, all its variations get deleted too.
    product = models.ForeignKey(Product, related_name='variations', on_delete=models.CASCADE)
    
    # Name of the variation, e.g., "Small, Red" or "KH-320 (Retail Box)"
    name = models.CharField(max_length=255)
    
    # The "variation price" from your blueprint
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # The "toggle" from your blueprint
    is_active = models.BooleanField(default=True)
    
    # How many of this specific variation you have
    stock_quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        # This will make it display nicely, e.g., "Fascial Gun KH-320 - Retail Box"
        return f"{self.product.name} - {self.name}"
    
# --- ADD THIS NEW CLASS ---
class Sale(models.Model):
    # links the sale to the logged-in user. Null=True allows old sales to exist.
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # This just records when the sale was made
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # This will make it display as "Sale #1", "Sale #2", etc.
        return f"Sale #{self.id}"

    # --- ADD THIS NEW FUNCTION ---
    @property
    def total_profit(self):
        # Get all items for this sale and sum their individual profits
        items = self.items.all()
        return sum(item.profit for item in items)


# --- AND ADD THIS NEW CLASS ---
class SaleItem(models.Model):
    # Link this item to its parent sale
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    
    # Link to the main product that was sold
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    # Link to the specific variation (if any)
    # blank=True, null=True means this field is OPTIONAL
    variation = models.ForeignKey(ProductVariation, on_delete=models.SET_NULL, blank=True, null=True)
    
    # How many were sold?
    quantity = models.PositiveIntegerField(default=1)
    
    # --- ADD THIS LINE ---
    # Store the buying_cost AT THE TIME of the sale
    buying_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # This is your "adjustable sell rate" feature.
    # We store the price AT THE TIME of the sale.
    sold_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    # --- ADD THIS NEW FUNCTION ---
    @property
    def profit(self):
        # Calculate the profit for this single line item
        return (self.sold_price - self.buying_cost) * self.quantity

    # This is the "magic" function that runs when you save
    def save(self, *args, **kwargs):
        # If this is a new sale item (not just an edit)
        if not self.pk: 
            # 1. Update the variation stock (if a variation was sold)
            if self.variation:
                self.variation.stock_quantity -= self.quantity
                self.variation.save()
            
            # 2. Update the main product's total stock
            self.product.stock_quantity -= self.quantity
            self.product.save()
            
        super().save(*args, **kwargs) # This actually saves the SaleItem

# ... (your Product, ProductVariation, Sale, SaleItem classes are here) ...

# --- ADD THIS NEW CLASS AT THE BOTTOM ---
class ProductImage(models.Model):
    # This is the "link" to the main product
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    
    # This is the new image field
    image = models.ImageField(upload_to='products/gallery/')
    
    def __str__(self):
        return f"Image for {self.product.name}"
    
# --- ADD THIS NEW CLASS AT THE BOTTOM ---
class CompetitorPrice(models.Model):
    # Link to the product this price is for
    product = models.ForeignKey(Product, related_name='competitor_prices', on_delete=models.CASCADE)

    website_name = models.CharField(max_length=100) # e.g., "Daraz", "StarTech"
    min_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_checked = models.DateTimeField(auto_now=True) # Automatically updates when saved

    def __str__(self):
        return f"{self.website_name} price for {self.product.name}"
    

# ... (all your existing models are here) ...
