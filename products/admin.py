from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import render
from .models import Product, ProductVariation, Sale, SaleItem, ProductImage , CompetitorPrice # Import ALL models


# --- NEW CLASS FOR THE GALLERY ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Show 1 blank "image" form by default

# --- ADD THIS NEW INLINE ---
class CompetitorPriceInline(admin.TabularInline):
    model = CompetitorPrice
    extra = 0 # Don't show blank forms, just display existing data
    readonly_fields = ('website_name', 'min_price', 'max_price', 'last_checked')
    can_delete = True

# --- This is your existing Product/Variation admin ---
class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1

# --- THIS IS THE NEW ADMIN ACTION FUNCTION ---
@admin.action(description="Print selected products")
def print_selected_products(modeladmin, request, queryset):
    # This function will be called when you select the action.
    # It redirects to a new view, passing the selected IDs in the URL.
    selected_ids = ",".join(str(product.id) for product in queryset)
    return HttpResponseRedirect(f"/print-products/?ids={selected_ids}")

class ProductAdmin(admin.ModelAdmin):
    # --- ADD THE NEW INLINE HERE ---
    inlines = [ProductImageInline, ProductVariationInline, CompetitorPriceInline]
    
    fieldsets = (
        (None, {
            # --- 'image' IS REMOVED FROM THIS LIST ---
            'fields': ('name', 'description')
        }),
        ('Pricing', {
            'fields': ('buying_cost', 'selling_price')
        }),
        ('Stock', {
            'fields': ('stock_quantity', 'box_quantity')
        }),
    )
    list_display = ('name', 'selling_price', 'stock_quantity', 'box_quantity')
    list_editable = ('selling_price', 'stock_quantity', 'box_quantity')
    actions = [print_selected_products]

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