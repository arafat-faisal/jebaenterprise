from django.contrib import admin
from django.db.models import Count, Q, Sum, F # <-- Added Sum and F
from .models import ProductEvent, SearchEvent
from jeba_inventory.models import Product

@admin.register(ProductEvent)
class ProductEventAdmin(admin.ModelAdmin):
    list_display = ('product', 'event_type', 'user', 'created_at')
    list_filter = ('event_type', 'created_at')

@admin.register(SearchEvent)
class SearchEventAdmin(admin.ModelAdmin):
    list_display = ('query', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('query',)

# --- ANALYTICS PROXY MODEL (Winning Products Dashboard) ---
class ProductAnalytics(Product):
    class Meta:
        proxy = True
        verbose_name = "Product Analytics (Winning Products)"
        verbose_name_plural = "Product Analytics (Winning Products)"
# --- In jeba_analytics/admin.py ---
@admin.register(ProductAnalytics)
class WinningProductAdmin(admin.ModelAdmin):
    # Added this line
    change_list_template = "admin/jeba_analytics/productanalytics/change_list.html" 
    
    list_display = ('name', 'product_revenue', 'product_profit', 'total_views', 'total_carts', 'total_orders', 'cart_conversion_rate', 'sales_conversion_rate')
    search_fields = ('name',)
    list_per_page = 50
    
    # We will need to set up a custom dashboard page next
    # change_list_template = "admin/jeba_analytics/productanalytics/change_list.html" 

    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            # Existing Event Counts
            views=Count('events', filter=Q(events__event_type='VIEW')),
            carts=Count('events', filter=Q(events__event_type='CART')),
            orders=Count('events', filter=Q(events__event_type='PURCHASE')),
            
            # --- NEW: Profit & Revenue Calculations ---
            total_revenue=Sum(F('saleitem__sold_price') * F('saleitem__quantity')),
            total_profit=Sum(
                (F('saleitem__sold_price') - F('saleitem__buying_cost')) * F('saleitem__quantity')
            ),
        ).filter(orders__gt=0).distinct() # Use distinct() to prevent duplicate rows from M2M/multi-join

        return qs.order_by('-total_profit', '-orders', '-carts', '-views')
    
    # Display methods for new fields (Format as Currency)
    def product_revenue(self, obj):
        # Format as ৳1,23,456
        return f"৳{obj.total_revenue:,.0f}" if obj.total_revenue else "৳0"
    product_revenue.admin_order_field = 'total_revenue'
    product_revenue.short_description = 'Total Revenue'

    def product_profit(self, obj):
        # Format as ৳1,23,456
        return f"৳{obj.total_profit:,.0f}" if obj.total_profit else "৳0"
    product_profit.admin_order_field = 'total_profit'
    product_profit.short_description = 'Total Profit'
    
    # Existing conversion methods remain
    def total_views(self, obj): return obj.views
    total_views.admin_order_field = 'views'

    def total_carts(self, obj): return obj.carts
    total_carts.admin_order_field = 'carts'

    def total_orders(self, obj): return obj.orders
    total_orders.admin_order_field = 'orders'

    def cart_conversion_rate(self, obj):
        if obj.views == 0: return "0%"
        return f"{((obj.carts / obj.views) * 100):.1f}%"

    def sales_conversion_rate(self, obj):
        if obj.views == 0: return "0%"
        return f"{((obj.orders / obj.views) * 100):.1f}%"