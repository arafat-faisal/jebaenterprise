from django.contrib import admin
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget

from .models import Category, Product, ProductVariation, ProductImage, Tag
from jeba_intelligence.models import CompetitorPrice
# Fix: Import the utility from its new modular home
from jeba_intelligence.utils import fetch_competitor_data

# --- BULK ACTIONS ---
# ... (Bulk actions remain unchanged, they are robust) ...
@admin.action(description='👁️ Hide Selected Products')
def hide_products(modeladmin, request, queryset):
    """Bulk hide products from the storefront."""
    updated_count = queryset.update(is_active=False)
    messages.success(request, f"Successfully hid {updated_count} products.")

@admin.action(description='👁️ Show Selected Products')
def show_products(modeladmin, request, queryset):
    """Bulk show products in the storefront."""
    updated_count = queryset.update(is_active=True)
    messages.success(request, f"Successfully made {updated_count} products visible.")

@admin.action(description='Auto-Assign Categories (AI-Lite)')
def auto_categorize_products(modeladmin, request, queryset):
    count = 0
    for product in queryset:
        if hasattr(product, 'auto_assign_category') and product.auto_assign_category():
            count += 1
    messages.success(request, f"Successfully categorized {count} products.")

@admin.action(description='Apply Smart Pricing (Comp. Avg - 50)')
def apply_smart_pricing(modeladmin, request, queryset):
    count = 0
    for product in queryset:
        if hasattr(product, 'apply_dynamic_pricing') and product.apply_dynamic_pricing():
            count += 1
    messages.success(request, f"Updated prices for {count} products.")

@admin.action(description="Print selected products")
def print_selected_products(modeladmin, request, queryset):
    selected_ids = ",".join(str(product.id) for product in queryset)
    return HttpResponseRedirect(f"/print-products/?ids={selected_ids}")

@admin.action(description="Auto-Check Competitor Prices")
def scrape_selected_products(modeladmin, request, queryset):
    success_count = 0
    fail_count = 0
    if queryset.count() > 5:
        messages.warning(request, "Please select fewer than 5 products at a time.")
        return
    for product in queryset:
        result = fetch_competitor_data(product)
        if result['success']: success_count += 1
        else: fail_count += 1
    messages.success(request, f"Updated {success_count} products. Failed: {fail_count}.")

# --- INLINES ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'transparent_image', 'is_main') # Added is_main for better control
    
class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1

class CompetitorPriceInline(admin.TabularInline):
    model = CompetitorPrice
    extra = 0
    readonly_fields = ('website_name', 'min_price', 'max_price', 'last_checked')
    can_delete = True

# --- REGISTRATIONS ---
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

class ProductResource(resources.ModelResource):
    category = Field(column_name='category', attribute='category', widget=ForeignKeyWidget(Category, 'name'))
    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'short_description', 'category', 'buying_cost', 'selling_price', 'stock_quantity', 'is_featured', 'call_for_price')
        import_id_fields = ('id',)

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    inlines = [ProductImageInline, ProductVariationInline, CompetitorPriceInline]
    
    # FIX: Added get_tags_display for visibility of SEO tags
    list_display = ('name', 'selling_price', 'stock_quantity', 'category', 'is_featured', 'is_active', 'call_for_price', 'get_tags_display', 'open_scraper_button')
    list_editable = ('selling_price', 'stock_quantity', 'is_featured', 'is_active', 'call_for_price')
    list_filter = ('is_active', 'is_featured', 'category', 'tags')
    search_fields = ('name', 'description')
    filter_horizontal = ('tags',)
    
    # Add the new actions to this list
    actions = [
        hide_products, 
        show_products, 
        print_selected_products, 
        auto_categorize_products, 
        apply_smart_pricing, 
        scrape_selected_products
    ]

    fieldsets = (
        (None, {'fields': ('name', 'category', 'is_active', 'is_featured', 'call_for_price')}),
        ('SEO & Searching', {'fields': ('tags',)}),
        ('Descriptions', {'fields': ('short_description', 'description')}),
        ('Pricing', {'fields': ('buying_cost', 'selling_price')}),
        ('Stock', {'fields': ('stock_quantity', 'box_quantity')}),
    )
    
    # FIX: Helper function to display tags nicely in the changelist
    def get_tags_display(self, obj):
        return ", ".join([tag.name for tag in obj.tags.all()])
    get_tags_display.short_description = "Tags"


    def open_scraper_button(self, obj):
        url = reverse('admin_scraper') + f'?product_id={obj.id}'
        return format_html('<a class="button" style="background-color: #17a2b8; color: white;" href="{}">Visual Match</a>', url)
    open_scraper_button.short_description = "Manual Tool"
    open_scraper_button.allow_tags = True

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)