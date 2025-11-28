from django.contrib import admin
from django import forms
from django.forms.widgets import TextInput
from .models import LandingPage, LandingSection
from django.utils.html import format_html

# --- 1. Custom Forms for Color Pickers ---

class LandingPageForm(forms.ModelForm):
    class Meta:
        model = LandingPage
        fields = '__all__'
        widgets = {
            'primary_color': TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; cursor: pointer;'}),
            'secondary_color': TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; cursor: pointer;'}),
            'accent_color': TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; cursor: pointer;'}),
            'text_color': TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; cursor: pointer;'}),
        }

class LandingSectionForm(forms.ModelForm):
    class Meta:
        model = LandingSection
        fields = '__all__'
        widgets = {
            'background_color': TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; cursor: pointer;'}),
            'text_color': TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; cursor: pointer;'}),
        }

# --- 2. Inline Section Editor ---

class LandingSectionInline(admin.StackedInline):
    model = LandingSection
    form = LandingSectionForm
    extra = 0
    min_num = 0
    classes = ('collapse-open',) # Optional: keeps sections open or closed by default
    
    fieldsets = (
        ('Layout & Type', {
            'fields': (
                ('section_type', 'order'),
                ('text_alignment', 'animation_effect'),
            ),
            'description': "Choose the structure and how elements animate in."
        }),
        ('Main Content', {
            'fields': ('icon_class', 'heading', 'subheading', 'description', 'button_text'),
            'description': "Add text and optional FontAwesome icon (e.g., 'fa-solid fa-star')."
        }),
        ('Visuals: Shapes & Spacing', {
            'fields': (
                ('divider_top', 'divider_bottom'),
                ('padding_top', 'padding_bottom'),
                ('border_radius', 'overlay_opacity')
            ),
            'classes': ('collapse',),
            'description': "Add wave/slant dividers, adjust vertical space, or round corners."
        }),
        ('Colors & Backgrounds', {
            'fields': (
                ('background_color', 'text_color'),
                'background_gradient',
            ),
            'classes': ('collapse',),
            'description': "Override global colors. Gradient example: 'linear-gradient(135deg, #ff00cc, #333399)'"
        }),
        ('Media Assets', {
            'fields': ('image', 'video_file', 'video_url'),
            'description': "Primary media for this section."
        }),
        ('Carousel Gallery (If Type = Carousel)', {
            'fields': (('image_2', 'image_3'), ('image_4', 'image_5')),
            'classes': ('collapse',),
        }),
    )

# --- 3. Main Page Admin ---

@admin.register(LandingPage)
class LandingPageAdmin(admin.ModelAdmin):
    form = LandingPageForm
    list_display = ('title', 'product_link', 'is_published', 'visit_page_link', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'product__name', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [LandingSectionInline]
    save_on_top = True
    
    fieldsets = (
        ("Campaign Info", {
            "fields": (("title", "slug"), ("product", "is_published"))
        }),
        ("🎨 Global Design Studio", {
            "fields": (
                ("font_heading", "font_body"),
                ("primary_color", "secondary_color"),
                ("accent_color", "text_color")
            ),
            "description": "Set the master theme. These fonts and colors apply to the whole page unless overridden in sections."
        }),
        ("Marketing Settings", {
            "fields": ("meta_pixel_id",),
            "classes": ("collapse",)
        }),
    )

    def product_link(self, obj):
        return obj.product.name
    product_link.short_description = "Product"

    def visit_page_link(self, obj):
        return format_html('<a href="/offers/{}/" target="_blank" class="button" style="background:#28a745; color:white;">👁 View Page</a>', obj.slug)
    visit_page_link.short_description = "Preview"