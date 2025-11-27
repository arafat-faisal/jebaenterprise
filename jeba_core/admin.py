from django.contrib import admin
from django.utils.html import format_html
from .models import SiteSettings

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    # List view provides a dashboard-like summary of the current config
    list_display = ('settings_label', 'mode_status', 'contact_summary', 'delivery_summary')
    list_display_links = ('settings_label',)
    
    fieldsets = (
        ("🔧 System & Maintenance", {
            'fields': ('maintenance_mode', 'call_for_price'),
            'description': "Master switches for site availability and pricing visibility."
        }),
        ("📢 Marketing & Hero Section", {
            'fields': ('featured_products',),
            'description': "Select specific products for the Homepage Hero Slider. If empty, standard featured products are used."
        }),
        ("💳 Commerce & Logistics", {
            'fields': (
                ('delivery_charge_inside', 'delivery_charge_outside'),
                'bkash_number'
            ),
            'description': "Manage delivery fees and payment information."
        }),
        ("🔗 Social & Tracking", {
            'fields': (
                ('facebook_page_url', 'messenger_username'),
                ('meta_pixel_id', 'meta_access_token')
            ),
            'classes': ('collapse',), # Collapsed by default to save space
            'description': "Configure Facebook integration and Meta Pixel tracking."
        }),
        ("📞 Contact Information", {
            'fields': (
                ('contact_phone', 'whatsapp_number'),
                'contact_email',
                'business_hours',
                'contact_address',
                'contact_message_template'
            ),
        }),
    )
    
    filter_horizontal = ('featured_products',)
    save_on_top = True # Puts a save button at the top for easier access

    # --- Singleton Protection ---
    def has_add_permission(self, request):
        # Only allow adding if no settings exist yet
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting the configuration
        return False

    # --- Custom Visuals ---
    def settings_label(self, obj):
        return "Global Configuration"
    settings_label.short_description = "Settings Object"

    def mode_status(self, obj):
        if obj.maintenance_mode:
            return format_html('<span style="color: white; background-color: red; padding: 3px 8px; border-radius: 10px; font-weight: bold;">⛔ Maintenance</span>')
        return format_html('<span style="color: white; background-color: green; padding: 3px 8px; border-radius: 10px; font-weight: bold;">✅ Live</span>')
    mode_status.short_description = "Site Status"

    def contact_summary(self, obj):
        return format_html(
            '<div><i class="fas fa-phone"></i> {}</div>'
            '<div><i class="fas fa-envelope"></i> {}</div>',
            obj.contact_phone,
            obj.contact_email
        )
    contact_summary.short_description = "Contact Info"

    def delivery_summary(self, obj):
        return format_html(
            'In: <b>{}</b> | Out: <b>{}</b>',
            obj.delivery_charge_inside,
            obj.delivery_charge_outside
        )
    delivery_summary.short_description = "Delivery Charges"