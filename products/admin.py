from django.contrib import admin
from .models import Product, ProductVariation, Sale, SaleItem  # Import ALL models

# --- This is your existing Product/Variation admin ---
class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1

class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductVariationInline]

admin.site.register(Product, ProductAdmin)
admin.site.register(ProductVariation)


# --- ADD THIS NEW CODE ---
class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1  # Show 1 blank "sale item" form by default
    
    # This makes the form "smart"
    # It will auto-fill 'sold_price' based on the product/variation
    # (This requires some advanced Javascript not included here,
    # but for now, you can enter it manually)
    fields = ('product', 'variation', 'quantity', 'buying_cost', 'sold_price')

class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = ('id', 'created_at', 'total_profit')
    readonly_fields = ('total_profit',) # Make it read-only
    
# Register your new Sale models
admin.site.register(Sale, SaleAdmin)