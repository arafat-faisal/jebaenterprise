from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import CompetitorPrice, ScraperPreset

@admin.register(ScraperPreset)
class ScraperPresetAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'confidence_visual', 
        'text_weight_display', 
        'image_weight_display', 
        'slam_dunk_visual'
    )
    list_editable = ('confidence_threshold', 'text_slam_dunk', 'image_slam_dunk')
    
    # We define editable fields in list_display but they must also be in list_editable
    # However, to show the visual AND edit, we usually keep visuals read-only or separate.
    # Let's keep it clean: Display visuals in list, edit in form.
    list_display = (
        'name', 
        'confidence_visual', 
        'text_visual',
        'image_visual'
    )
    list_editable = () # Reset for safety in this view
    
    fieldsets = (
        ("Preset Identity", {
            "fields": ('name',)
        }),
        ("Matching Weights (0.0 - 1.0)", {
            "fields": ('text_weight', 'image_weight'),
            "description": "How much importance to give to Text vs Image matching."
        }),
        ("Thresholds (0 - 100)", {
            "fields": ('confidence_threshold', 'text_slam_dunk', 'image_slam_dunk'),
            "description": "Scores required to consider a match valid or 'perfect'."
        }),
    )

    def confidence_visual(self, obj):
        val = obj.confidence_threshold
        color = "success" if val >= 80 else "warning" if val >= 50 else "danger"
        return format_html(
            '<div style="width: 100px; background: #e9ecef; border-radius: 4px; overflow: hidden;">'
            '<div style="width: {}%; background-color: var(--{}); height: 6px;"></div>'
            '</div><span style="font-size: 10px; font-weight: bold;">{}% Min</span>',
            val, color, val
        )
    confidence_visual.short_description = "Confidence Thresh."

    def text_visual(self, obj):
        return f"Weight: {obj.text_weight} | Dunk: {obj.text_slam_dunk}"
    text_visual.short_description = "Text Logic"

    def image_visual(self, obj):
        return f"Weight: {obj.image_weight} | Dunk: {obj.image_slam_dunk}"
    image_visual.short_description = "Image Logic"


@admin.register(CompetitorPrice)
class CompetitorPriceAdmin(admin.ModelAdmin):
    list_display = (
        'product_link', 
        'website_badge', 
        'price_range_visual', 
        'last_checked_display'
    )
    list_filter = ('website_name', 'last_checked')
    search_fields = ('product__name', 'website_name')
    list_select_related = ('product',)
    list_per_page = 25

    def product_link(self, obj):
        url = reverse("admin:jeba_inventory_product_change", args=[obj.product.id])
        return format_html(
            '<a href="{}" style="font-weight: bold; color: var(--info);">'
            '<i class="fas fa-box"></i> {}</a>',
            url, obj.product.name
        )
    product_link.short_description = "Product"

    def website_badge(self, obj):
        return format_html(
            '<span class="badge badge-primary">{}</span>', 
            obj.website_name
        )
    website_badge.short_description = "Source"

    def price_range_visual(self, obj):
        if not obj.min_price:
            return "-"
        
        diff = 0
        if obj.max_price and obj.min_price:
            diff = obj.max_price - obj.min_price
            
        if diff > 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{} Tk</span>'
                ' <span style="color: #6c757d; font-size: 0.9em;">⮕ {} Tk</span>',
                obj.min_price, obj.max_price
            )
        return format_html('<span style="font-weight: bold;">{} Tk</span>', obj.min_price)
    price_range_visual.short_description = "Market Price"

    def last_checked_display(self, obj):
        if not obj.last_checked:
            return "-"
        return obj.last_checked.strftime("%Y-%m-%d %H:%M")
    last_checked_display.short_description = "Scraped At"