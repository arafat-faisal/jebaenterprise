from django.contrib import admin
from .models import GlobalSEOSettings, StaticPageSEO
from django.urls import path
from django.shortcuts import render
from django.core.management import call_command
from django.contrib import messages
import io

@admin.register(GlobalSEOSettings)
class GlobalSEOSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'default_meta_title')
    # Singleton pattern: Ensure only one settings object exists
    def has_add_permission(self, request):
        return not GlobalSEOSettings.objects.exists()

@admin.register(StaticPageSEO)
class StaticPageSEOAdmin(admin.ModelAdmin):
    list_display = ('page_name', 'meta_title', 'meta_description')
    list_editable = ('meta_title', 'meta_description')

# 1. Create a dummy model for the menu item
from .models import GlobalSEOSettings # Reuse existing or create a proxy
class SEODashboard(GlobalSEOSettings):
    class Meta:
        proxy = True
        verbose_name = "🚀 AI Command Panel"
        verbose_name_plural = "🚀 AI Command Panel"

# 2. Register the View
@admin.register(SEODashboard)
class SEODashboardAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_site.admin_view(self.dashboard_view), name='seo_dashboard'),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        output = ""
        if request.method == "POST":
            command = request.POST.get('command')
            
            # Capture console output
            out = io.StringIO()
            try:
                if command == 'optimize_bulk':
                    call_command('optimize_bulk', stdout=out)
                    messages.success(request, "Bulk Optimization batch completed!")
                elif command == 'organize_inventory':
                    call_command('organize_inventory', stdout=out)
                    messages.success(request, "Inventory Organization completed!")
                
                output = out.getvalue()
            except Exception as e:
                output = f"Error: {str(e)}"
                messages.error(request, "Command failed.")

        context = dict(
            self.admin_site.each_context(request),
            output=output,
        )
        return render(request, "admin/jeba_seo/dashboard.html", context)