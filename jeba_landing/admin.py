from django.contrib import admin
from django import forms
from django.forms.widgets import TextInput
from .models import LandingPage, LandingSection
from django.utils.html import format_html

# --- Custom Form for Color Picker ---
class LandingSectionForm(forms.ModelForm):
    class Meta:
        model = LandingSection
        fields = '__all__'
        widgets = {
            'background_color': TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; cursor: pointer;'}),
            'text_color': TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; cursor: pointer;'}),
        }

# --- Inline Section Editor ---
class LandingSectionInline(admin.StackedInline):
    model = LandingSection
    form = LandingSectionForm
    extra = 0
    min_num = 1
    fieldsets = (
        ('Layout & Animation', {
            'fields': (('order', 'section_type', 'animation_effect'),)
        }),
        ('Content', {
            'fields': ('heading', 'subheading', 'description', 'button_text')
        }),
        ('Design & Positioning', {
            'fields': (('text_alignment', 'overlay_opacity'), ('background_color', 'text_color')),
            'description': "Control text alignment and image overlay darkness."
        }),
        ('Media (Main)', {
            'fields': ('image', 'video_file', 'video_url')
        }),
        ('Carousel Gallery', {
            'fields': (('image_2', 'image_3'), ('image_4', 'image_5')),
            'classes': ('collapse',),
        }),
    )

@admin.register(LandingPage)
class LandingPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'product_link', 'status_badge', 'visit_page_link', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'product__name', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [LandingSectionInline]
    
    fieldsets = (
        ("Campaign Details", {
            "fields": ("title", "slug", "is_published")
        }),
        ("Linked Product", {
            "fields": ("product",),
            "description": "The 'Buy Now' button will add this product to the cart."
        }),
        ("Marketing & Analytics", {
            "fields": ("meta_pixel_id",),
            "classes": ("collapse",)
        }),
    )

    def product_link(self, obj):
        return obj.product.name
    product_link.short_description = "Promoted Product"

    def status_badge(self, obj):
        if obj.is_published:
            return format_html('<span style="color: green; font-weight: bold;">✔ Live</span>')
        return format_html('<span style="color: orange; font-weight: bold;">✎ Draft</span>')
    status_badge.short_description = "Status"

    def visit_page_link(self, obj):
        return format_html('<a href="/offers/{}/" target="_blank" class="button">View Page</a>', obj.slug)
    visit_page_link.short_description = "Preview"