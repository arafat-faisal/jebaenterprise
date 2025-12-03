from django.contrib import admin
from django import forms
from django.forms.widgets import TextInput, Textarea
from .models import LandingPage, LandingSection, LandingTheme
from django.utils.html import format_html
from django.urls import reverse

# --- 1. Theme Manager ---
@admin.register(LandingTheme)
class LandingThemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}

# --- 2. Custom Forms & Widgets ---

class LandingPageForm(forms.ModelForm):
    class Meta:
        model = LandingPage
        fields = '__all__'
        widgets = {
            # Corrected Field Names
            'override_primary_color': TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; cursor: pointer;'}),
            'override_accent_color': TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; cursor: pointer;'}),
            'custom_css': Textarea(attrs={'rows': 10, 'style': 'font-family: monospace; width: 100%; background: #1e1e1e; color: #d4d4d4;'}),
        }

class LandingSectionForm(forms.ModelForm):
    class Meta:
        model = LandingSection
        fields = '__all__'
        widgets = {
            'background_color': TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; cursor: pointer;'}),
            'text_color': TextInput(attrs={'type': 'color', 'style': 'height: 40px; width: 80px; cursor: pointer;'}),
        }

# --- 3. Inline Section Editor ---

class LandingSectionInline(admin.StackedInline):
    model = LandingSection
    form = LandingSectionForm
    extra = 0
    min_num = 0
    classes = ('collapse-open',)
    sortable_field_name = "order"
    
    fieldsets = (
        ('Layout & Animation', {
            'fields': (
                ('section_type', 'order'),
                ('text_alignment', 'animation_effect'),
            ),
        }),
        ('Content', {
            'fields': ('icon_class', 'heading', 'subheading', 'description', 'button_text'),
        }),
        ('Visuals & Spacing', {
            'fields': (
                ('divider_top', 'divider_bottom'),
                ('padding_top', 'padding_bottom'),
                ('border_radius', 'overlay_opacity'),
                ('desktop_media_position', 'mobile_media_position'),
            ),
            'classes': ('collapse',),
        }),
        ('Colors & Backgrounds', {
            'fields': (
                ('background_color', 'text_color'),
                'background_gradient',
            ),
            'classes': ('collapse',),
        }),
        ('Media Assets', {
            'fields': ('image', 'video_file', 'video_url'),
        }),
        ('Carousel Items', {
            'fields': (('image_2', 'image_3'), ('image_4', 'image_5')),
            'classes': ('collapse',),
        }),
    )

# --- 4. Main Page Admin ---

@admin.register(LandingPage)
class LandingPageAdmin(admin.ModelAdmin):
    form = LandingPageForm
    list_display = ('title', 'product_link', 'is_published', 'visit_page_link', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'product__name', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [LandingSectionInline]
    save_on_top = True
    change_form_template = 'admin/jeba_landing/landingpage/change_form.html'
    
    fieldsets = (
        ("Campaign Info", {
            "fields": (("title", "slug"), ("product", "is_published"))
        }),
        ("🎨 Design System", {
            "fields": (
                ("theme", "theme_preset"),
                # Corrected Field Names
                ("override_primary_color", "override_accent_color"),
                ("font_heading", "font_body"),
                "custom_css"
            ),
            "description": "Select a global theme or override specific colors."
        }),
        ("⚡ Conversion Tools", {
            "fields": (
                ("countdown_end", "stock_warning"),
                "trust_badge_image"
            ),
        }),
        ("Marketing Settings", {
            "fields": ("meta_pixel_id", "ai_generated"),
            "classes": ("collapse",)
        }),
    )

    def product_link(self, obj):
        return obj.product.name if obj.product else "-"
    product_link.short_description = "Product"

    def visit_page_link(self, obj):
        try:
            url = reverse('landing_page_detail', args=[obj.slug])
            return format_html('<a href="{}" target="_blank" class="button" style="background:#28a745; color:white;">👁 View Page</a>', url)
        except Exception:
            return "-"
    visit_page_link.short_description = "Preview"