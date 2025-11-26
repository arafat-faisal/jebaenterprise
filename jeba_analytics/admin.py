from django.contrib import admin
from django.db.models import Count, Q
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

# --- Winning Product Dashboard ---
class ProductAnalytics(Product):
    class Meta:
        proxy = True
        verbose_name = "Product Analytics (Winning Products)"
        verbose_name_plural = "Product Analytics (Winning Products)"

@admin.register(ProductAnalytics)
class WinningProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'total_views', 'total_carts', 'total_orders', 'cart_conversion_rate', 'sales_conversion_rate')
    search_fields = ('name',)
    list_per_page = 50

    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            views=Count('events', filter=Q(events__event_type='VIEW')),
            carts=Count('events', filter=Q(events__event_type='CART')),
            orders=Count('events', filter=Q(events__event_type='PURCHASE')),
        )
        return qs.order_by('-orders', '-carts', '-views')

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