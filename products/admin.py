from django.contrib import admin
from django.http import HttpResponseRedirect
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import timedelta

from .models import Product, ProductVariation, Sale, SaleItem, ProductImage, CompetitorPrice, Category

# --- 1. Existing Inlines (No Changes) ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class CompetitorPriceInline(admin.TabularInline):
    model = CompetitorPrice
    extra = 0
    readonly_fields = ('website_name', 'min_price', 'max_price', 'last_checked')
    can_delete = True

class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    fields = ('product', 'variation', 'quantity', 'buying_cost', 'sold_price')

# --- 2. Admin Actions (No Changes) ---
@admin.action(description="Print selected products")
def print_selected_products(modeladmin, request, queryset):
    selected_ids = ",".join(str(product.id) for product in queryset)
    return HttpResponseRedirect(f"/print-products/?ids={selected_ids}")

# --- 3. Product Admin (No Changes) ---
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductVariationInline, CompetitorPriceInline]
    fieldsets = (
        (None, {'fields': ('name', 'description', 'category')}),
        ('Pricing', {'fields': ('buying_cost', 'selling_price')}),
        ('Stock', {'fields': ('stock_quantity', 'box_quantity')}),
    )
    list_display = ('name', 'selling_price', 'stock_quantity', 'category')
    list_editable = ('selling_price', 'stock_quantity')
    actions = [print_selected_products]

# --- 4. NEW: Smart Sales Admin Dashboard ---
class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = ('id', 'customer_name', 'status', 'created_at', 'total_profit')
    list_filter = ('status', 'created_at')
    search_fields = ('customer_name', 'phone_number', 'id')
    readonly_fields = ('total_profit',)

    # This function injects chart data into the admin page
    def changelist_view(self, request, extra_context=None):
        # A. Calculate Sales for Last 30 Days
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        sales_data = (
            SaleItem.objects
            .filter(sale__created_at__range=(start_date, end_date))
            .annotate(date=TruncDate('sale__created_at'))
            .values('date')
            .annotate(total_sales=Sum('sold_price'))
            .order_by('date')
        )

        # Format data for Chart.js
        dates = [entry['date'].strftime('%Y-%m-%d') for entry in sales_data]
        totals = [float(entry['total_sales']) for entry in sales_data]

        # B. Find Low Stock Products (Threshold < 5)
        low_stock_products = Product.objects.filter(stock_quantity__lt=5)[:5]

        # C. Pass data to the template
        extra_context = extra_context or {}
        extra_context['chart_dates'] = json.dumps(dates, cls=DjangoJSONEncoder)
        extra_context['chart_totals'] = json.dumps(totals, cls=DjangoJSONEncoder)
        extra_context['low_stock_products'] = low_stock_products

        return super().changelist_view(request, extra_context=extra_context)

# --- 5. Register Models ---
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductVariation)
admin.site.register(Sale, SaleAdmin)
admin.site.register(Category)