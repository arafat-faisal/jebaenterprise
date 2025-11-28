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
from jeba_intelligence.utils import fetch_competitor_data

# --- BULK ACTIONS ---
@admin.action(description='👁️ Hide Selected Products')
def hide_products(modeladmin, request, queryset):
    updated_count = queryset.update(is_active=False)
    messages.success(request, f"Successfully hid {updated_count} products.")

@admin.action(description='👁️ Show Selected Products')
def show_products(modeladmin, request, queryset):
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
    fields = ('image', 'image_preview', 'transparent_image', 'is_main') 
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 80px; height: auto; border-radius: 5px;" />', obj.image.url)
        return "-"
    image_preview.short_description = "Preview"

class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1
    fields = ('name', 'selling_price', 'stock_quantity', 'is_active')

class CompetitorPriceInline(admin.TabularInline):
    model = CompetitorPrice
    extra = 0
    readonly_fields = ('website_name', 'min_price', 'max_price', 'last_checked')
    can_delete = True

# --- RESOURCES ---
class ProductResource(resources.ModelResource):
    category = Field(column_name='category', attribute='category', widget=ForeignKeyWidget(Category, 'name'))
    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'short_description', 'category', 'buying_cost', 'original_price', 'selling_price', 'stock_quantity', 'is_featured', 'call_for_price')
        import_id_fields = ('id',)

# --- ADMIN REGISTRATIONS ---
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_count')
    search_fields = ('name',)

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "Products"

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    inlines = [ProductImageInline, ProductVariationInline, CompetitorPriceInline]
    
    # List View Configuration
    list_display = (
        'thumbnail_preview', 
        'name', 
        'category', 
        'original_price', # Added to list view
        'selling_price', 
        'stock_quantity', 
        'is_active', 
        'is_featured', 
        'get_tags_display', 
        'open_scraper_button'
    )
    list_display_links = ('thumbnail_preview', 'name')
    list_editable = ('selling_price', 'original_price', 'stock_quantity', 'is_active', 'is_featured')
    list_filter = ('is_active', 'is_featured', 'category', 'tags')
    search_fields = ('name', 'description', 'id')
    filter_horizontal = ('tags',)
    list_per_page = 20
    
    actions = [
        hide_products, 
        show_products, 
        print_selected_products, 
        auto_categorize_products, 
        apply_smart_pricing, 
        scrape_selected_products
    ]

    # Detail View Layout
    fieldsets = (
        ("✨ Basic Info", {
            "fields": ('name', 'category', 'is_active', 'is_featured', 'call_for_price')
        }),
        ("💰 Pricing & Stock", {
            # UPDATED: Grouped pricing fields for better UX
            "fields": (
                'buying_cost', 
                ('original_price', 'selling_price'), # Side-by-side
                ('stock_quantity', 'box_quantity')
            )
        }),
        ("🔎 SEO & Meta", {
            "fields": ('tags', 'short_description', 'description', 'created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    # --- CUSTOM METHODS ---
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px; border: 1px solid #ccc;" />', obj.thumbnail.url)
        return format_html('<span style="color: #ccc;">No Image</span>')
    thumbnail_preview.short_description = "Image"

    def get_tags_display(self, obj):
        tags = [tag.name for tag in obj.tags.all()]
        if not tags:
            return "-"
        return ", ".join(tags)
    get_tags_display.short_description = "Tags"

    def open_scraper_button(self, obj):
        url = reverse('admin_scraper') + f'?product_id={obj.id}'
        return format_html(
            '<a class="button" style="background-color: #17a2b8; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none;" href="{}">'
            '<i class="fas fa-search-dollar"></i> Check Price</a>', 
            url
        )
    open_scraper_button.short_description = "Intelligence"
    open_scraper_button.allow_tags = True