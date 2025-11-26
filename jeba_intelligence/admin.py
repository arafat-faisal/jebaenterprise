from django.contrib import admin
from .models import CompetitorPrice, ScraperPreset

@admin.register(ScraperPreset)
class ScraperPresetAdmin(admin.ModelAdmin):
    list_display = ('name', 'confidence_threshold', 'text_slam_dunk')

@admin.register(CompetitorPrice)
class CompetitorPriceAdmin(admin.ModelAdmin):
    list_display = ('product', 'website_name', 'min_price', 'max_price', 'last_checked')
    list_filter = ('website_name',)