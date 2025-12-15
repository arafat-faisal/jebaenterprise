from django.contrib import admin
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget

from .models import Category, Product, ProductVariation, ProductImage, Tag, ProductVariant
from jeba_intelligence.models import CompetitorPrice
from jeba_intelligence.utils import fetch_competitor_data


# --- ACTION: Multiple Selected ---
@admin.action(description='✨ Generate AI Content for Selected')
def generate_ai_selected(modeladmin, request, queryset):
    # This just redirects each one to our view (simplified) or loops logic
    # Ideally, call the logic directly here for bulk, but reusing the view is easiest:
    from jeba_seo.views import generate_ai_for_product
    count = 0
    for product in queryset:
        generate_ai_for_product(request, product.id) # Reuses logic
        count += 1
    modeladmin.message_user(request, f"Queued AI generation for {count} products.")

@admin.action(description='Apply AI Categories (Auto-Create New) & Tags')
def apply_ai_organization(modeladmin, request, queryset):
    applied_count = 0
    created_categories = []
    
    for product in queryset:
        # 1. Apply Category (The Intelligent Part)
        if product.ai_suggested_category:
            cat_name = product.ai_suggested_category.strip()
            
            # Try to get existing, or CREATE if missing
            category, created = Category.objects.get_or_create(
                name__iexact=cat_name,
                defaults={'name': cat_name}
            )
            
            if created and cat_name not in created_categories:
                created_categories.append(cat_name)
            
            product.category = category
                
        # 2. Apply Tags
        if product.ai_suggested_tags:
            tag_names = [t.strip() for t in product.ai_suggested_tags.split(',')]
            for t_name in tag_names:
                tag, _ = Tag.objects.get_or_create(name=t_name)
                product.tags.add(tag)
                
        product.save()
        applied_count += 1

    # Feedback Message
    if created_categories:
        modeladmin.message_user(request, f"Success! Created {len(created_categories)} new categories: {', '.join(created_categories)}.")
    
    modeladmin.message_user(request, f"Updated {applied_count} products with AI data.")

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
    # UPGRADE: Added SKU and Original Price
    fields = ('name', 'sku', 'original_price', 'selling_price', 'stock_quantity', 'image', 'is_active')

class ProductVariantInline(admin.TabularInline):
    """Inline for new ProductVariant model (color/size/material variants)"""
    model = ProductVariant
    extra = 1
    fields = ('variant_type', 'name', 'color_code', 'price_adjustment', 'stock_quantity', 'sku', 'is_active', 'sort_order')
    


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
    inlines = [ProductImageInline, ProductVariantInline, ProductVariationInline, CompetitorPriceInline]
    
    # List View Configuration
    list_display = (
        'thumbnail_preview', 
        'name', 
        'category', 
        'original_price', # Added to list view
        'selling_price', 
        'stock_quantity', 
        'is_active', 
        'is_seo_optimized',
        'use_ai_name',
        'use_ai_short_description',
        'use_ai_description',
        'is_featured', 
        'get_tags_display', 
        'open_scraper_button',
        'get_tags_count',
        'ai_suggested_category',
        'ai_status_button'
    )
    list_display_links = ('thumbnail_preview', 'name')
    list_editable = ('selling_price', 'original_price', 'stock_quantity', 'is_active', 'is_featured', 'use_ai_name', 'use_ai_short_description','use_ai_description')
    list_filter = ('is_active', 'is_featured', 'category', 'tags', 'is_seo_optimized', 'use_ai_name')
    search_fields = ('name', 'description', 'id', 'ai_suggested_name', 'meta_title_ai')
    filter_horizontal = ('tags',)
    list_per_page = 20
    
    actions = [
        generate_ai_selected,
        hide_products, 
        show_products, 
        print_selected_products, 
        auto_categorize_products, 
        apply_smart_pricing, 
        scrape_selected_products,
        apply_ai_organization,
        
    ]
    readonly_fields = ('created_at', 'updated_at', 'meta_title_ai', 'meta_description_ai', 'ai_suggested_name', 'ai_suggested_description','is_seo_optimized','generate_ai_button')
    
    # Column Button (For List View)
    def ai_status_button(self, obj):
        # FIX: Ensure object is saved before generating links
        if not obj or not obj.id:
            return "-"
        if obj.is_seo_optimized:
            return format_html('<span style="color:green;">✅ Optimized</span>')
        url = reverse('generate_ai_product', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" style="background:#6610f2; color:white; padding:3px 8px; border-radius:4px;">✨ Auto-Fill</a>', 
            url
        )
    ai_status_button.short_description = "AI Action"

    # Field Button (For Edit Page)
    def generate_ai_button(self, obj):
        # FIX: Ensure object is saved before generating links
        if not obj or not obj.id:
            return "Save the product first to enable AI features."
        
        url = reverse('generate_ai_product', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" style="background:#6610f2; color:white; padding:8px 16px; border-radius:4px; font-weight:bold;">✨ Generate All AI Content Now</a>', 
            url
        )
    generate_ai_button.short_description = "AI Generator"

    # Detail View Layout
    fieldsets = (
        ("✨ Basic Info", {
            "fields": ('name', 'category', 'is_active', 'is_featured', 'call_for_price')
        }),
        # --- NEW SECTION: AI CONTENT ARCHITECT ---
        ("AI Content Architect (Bangladesh)", {
            "fields": (
                "generate_ai_button",
                "use_ai_name", "ai_suggested_name", 
                "use_ai_short_description", "ai_suggested_short_description", # <--- Added here
                "use_ai_description", "ai_suggested_description"
            ),
            "description": "Toggle the checkboxes to display the AI-generated content on the website instead of your manual content.",
            "classes": ("collapse",), # Click to expand
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
        ("SEO Settings (AI Generated)", {
            "fields": ("is_seo_optimized", "meta_title_ai", "meta_description_ai"),
            "classes": ("collapse",),
        }),
        ("AI Inventory Organizer", {
            "fields": ("ai_suggested_category", "ai_suggested_tags"),
            "description": "Run the 'organize_inventory' command to fill these. Then select 'Apply AI Organization' action to save them.",
            "classes": ("collapse",),
        }),
    )
    
    def get_tags_count(self, obj):
        return obj.tags.count()
    get_tags_count.short_description = 'Tags'
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
        # FIX: Ensure object is saved before generating links
        if not obj or not obj.id:
            return "-"
            
        url = reverse('admin_scraper') + f'?product_id={obj.id}'
        return format_html(
            '<a class="button" style="background-color: #17a2b8; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none;" href="{}">'
            '<i class="fas fa-search-dollar"></i> Check Price</a>', 
            url
        )
    open_scraper_button.short_description = "Intelligence"
    open_scraper_button.allow_tags = True