from django.contrib import admin
from .models import PageReport

@admin.register(PageReport)
class PageReportAdmin(admin.ModelAdmin):
    list_display = ('url', 'performance_score', 'total_time_ms', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('url',)
    readonly_fields = ('created_at', 'details')
