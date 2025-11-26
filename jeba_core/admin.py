from django.contrib import admin
from jeba_core.models import SiteSettings

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    filter_horizontal = ('featured_products',)
    
    fieldsets = (
        ('General Configuration', {
            'fields': ('maintenance_mode', 'call_for_price')
        }),
        ('Homepage Marketing', {
            'fields': ('featured_products',),
            'description': "Select products here to override the default 'Featured' list on the homepage."
        }),
        ('E-commerce Settings', {
            'fields': ('meta_pixel_id', 'meta_access_token', 'delivery_charge_inside', 'delivery_charge_outside', 'messenger_username', 'facebook_page_url')
        }),
        ('Contact & Support', {
            'fields': ('contact_phone', 'contact_email', 'contact_address', 'business_hours', 'whatsapp_number', 'contact_message_template')
        }),
    )
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False