from django.contrib import admin
from django.db.models import Count, Q, Sum, F, ExpressionWrapper, DecimalField
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta

# --- MODELS ---
from .models import ProductEvent, SearchEvent, DailyAdSpend
from jeba_inventory.models import Product
from jeba_sales.models import SaleItem

# --- 1. DAILY PROFIT & ROI DASHBOARD ---
@admin.register(DailyAdSpend)
class DailyAdSpendAdmin(admin.ModelAdmin):
    list_display = (
        'date_display', 
        'facebook_spend', 
        'google_spend', 
        'tiktok_spend',
        'marketing_cost_total', 
        'daily_revenue', 
        'daily_net_profit', 
        'daily_roas'
    )
    list_editable = ('facebook_spend', 'google_spend', 'tiktok_spend')
    list_per_page = 31 
    ordering = ('-date',)
    
    fieldsets = (
        ("📅 Date & Spend", {
            'fields': ('date', 'facebook_spend', 'google_spend', 'tiktok_spend')
        }),
        ("📊 Cached Stats (Auto-Updated)", {
            'fields': ('total_revenue', 'total_profit', 'total_orders'),
            'classes': ('collapse',),
            'description': "These fields update automatically based on Sales data."
        })
    )

    def date_display(self, obj):
        return obj.date.strftime("%d %b, %Y (%a)")
    date_display.short_description = "Date"
    date_display.admin_order_field = 'date'

    def marketing_cost_total(self, obj):
        return f"৳{obj.total_spend:,.0f}"
    marketing_cost_total.short_description = "Total Spend"

    # --- DYNAMIC METRICS ---
    def get_sales_data(self, date):
        return SaleItem.objects.filter(
            sale__created_at__date=date,
            sale__status__in=['PROCESSING', 'SHIPPED', 'DELIVERED']
        ).aggregate(
            rev=Sum(F('sold_price') * F('quantity')),
            cost=Sum(F('buying_cost') * F('quantity'))
        )

    def daily_revenue(self, obj):
        data = self.get_sales_data(obj.date)
        revenue = data['rev'] or 0
        return format_html(f"<b>৳{revenue:,.0f}</b>")
    daily_revenue.short_description = "Revenue"

    def daily_net_profit(self, obj):
        data = self.get_sales_data(obj.date)
        revenue = data['rev'] or 0
        cogs = data['cost'] or 0
        gross = revenue - cogs
        net = gross - obj.total_spend
        
        color = "green" if net > 0 else "red"
        return format_html(f"<span style='color:{color}; font-weight:bold;'>৳{net:,.0f}</span>")
    daily_net_profit.short_description = "Net Profit"

    def daily_roas(self, obj):
        data = self.get_sales_data(obj.date)
        revenue = data['rev'] or 0
        if obj.total_spend > 0:
            roas = revenue / obj.total_spend
            color = "green" if roas >= 3 else "orange" if roas >= 1.5 else "red"
            return format_html(f"<span style='color:{color}; font-weight:bold;'>{roas:.2f}x</span>")
        return "-"
    daily_roas.short_description = "ROAS"


# --- 2. WINNING PRODUCTS INTELLIGENCE ---
class ProductAnalytics(Product):
    class Meta:
        proxy = True
        verbose_name = "Product Funnel & Analytics"
        verbose_name_plural = "Product Funnel & Analytics"

@admin.register(ProductAnalytics)
class WinningProductAdmin(admin.ModelAdmin):
    change_list_template = "admin/jeba_analytics/productanalytics/change_list.html" 
    
    # Updated columns to focus on the "Funnel"
    list_display = (
        'name', 
        'funnel_visual',       # Visual bar showing View -> Cart -> Order
        'view_to_cart_rate',   # "Add to Cart Rate"
        'cart_abandonment',    # "Added but not bought"
        'sales_conversion',    # Overall success
        'product_profit_display'
    )
    search_fields = ('name',)
    list_per_page = 50
    show_full_result_count = False

    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            views=Count('events', filter=Q(events__event_type='VIEW')),
            carts=Count('events', filter=Q(events__event_type='CART')),
            orders=Count('events', filter=Q(events__event_type='PURCHASE')),
            
            total_revenue=Sum(
                F('saleitem__sold_price') * F('saleitem__quantity'),
                filter=Q(saleitem__sale__status__in=['PROCESSING', 'SHIPPED', 'DELIVERED'])
            ),
            total_cost=Sum(
                F('saleitem__buying_cost') * F('saleitem__quantity'),
                filter=Q(saleitem__sale__status__in=['PROCESSING', 'SHIPPED', 'DELIVERED'])
            ),
        )
        
        qs = qs.annotate(
            calculated_profit=ExpressionWrapper(
                F('total_revenue') - F('total_cost'),
                output_field=DecimalField()
            )
        ).distinct()

        return qs.order_by(F('calculated_profit').desc(nulls_last=True))

    # --- FUNNEL METRICS ---

    def funnel_visual(self, obj):
        """Visualizes the drop-off from View to Order."""
        views = obj.views or 0
        carts = obj.carts or 0
        orders = obj.orders or 0
        
        # Prevent division by zero
        if views == 0: return "-"
        
        # Calculate percentages relative to Views
        cart_pct = min(100, int((carts / views) * 100))
        order_pct = min(100, int((orders / views) * 100))
        
        return format_html(
            '''
            <div style="min-width: 150px;">
                <div style="font-size: 10px; color: #666; margin-bottom: 2px;">
                    👁️ {v} &nbsp; 🛒 {c} &nbsp; 💰 {o}
                </div>
                <div style="width: 100%; background: #eee; height: 6px; border-radius: 3px; margin-bottom: 2px;">
                    <div style="width: 100%; background: #17a2b8; height: 100%; border-radius: 3px;"></div>
                </div>
                <div style="width: 100%; background: #eee; height: 6px; border-radius: 3px; margin-bottom: 2px;">
                    <div style="width: {cp}%; background: #ffc107; height: 100%; border-radius: 3px;"></div>
                </div>
                <div style="width: 100%; background: #eee; height: 6px; border-radius: 3px;">
                    <div style="width: {op}%; background: #28a745; height: 100%; border-radius: 3px;"></div>
                </div>
            </div>
            ''',
            v=views, c=carts, o=orders, cp=cart_pct, op=order_pct
        )
    funnel_visual.short_description = "Funnel (View > Cart > Buy)"

    def view_to_cart_rate(self, obj):
        """High View, Low Cart = People don't like the price/offer."""
        if obj.views == 0: return "-"
        rate = (obj.carts / obj.views) * 100
        
        color = "red" if rate < 2 else "green"
        return format_html(f"<span style='color:{color}; font-weight:bold;'>{rate:.1f}%</span>")
    view_to_cart_rate.short_description = "Add-to-Cart %"
    view_to_cart_rate.admin_order_field = 'carts'

    def cart_abandonment(self, obj):
        """High Cart, Low Order = Checkout Issue or Shipping Cost."""
        if obj.carts == 0: return "-"
        
        # Abandoned = Carts that did NOT become orders
        abandoned_carts = obj.carts - obj.orders
        rate = (abandoned_carts / obj.carts) * 100
        
        # High abandonment is BAD (Red)
        color = "red" if rate > 70 else "orange" if rate > 50 else "green"
        return format_html(f"<span style='color:{color}; font-weight:bold;'>{rate:.1f}%</span>")
    cart_abandonment.short_description = "Abandonment %"

    def sales_conversion(self, obj):
        """Overall Views to Orders."""
        if obj.views == 0: return "-"
        rate = (obj.orders / obj.views) * 100
        return f"{rate:.2f}%"
    sales_conversion.short_description = "Overall Conv."
    sales_conversion.admin_order_field = 'orders'

    def product_profit_display(self, obj):
        val = obj.calculated_profit or 0
        return f"৳{val:,.0f}"
    product_profit_display.short_description = "Profit"
    product_profit_display.admin_order_field = 'calculated_profit'


# --- 3. RAW EVENT LOGS ---
@admin.register(ProductEvent)
class ProductEventAdmin(admin.ModelAdmin):
    list_display = ('product', 'event_type', 'user_or_guest', 'price_captured', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('product__name', 'session_id')
    
    def user_or_guest(self, obj):
        if obj.user:
            return obj.user.username
        if obj.session_id:
            return f"Guest ({obj.session_id[:8]}...)"
        return "Guest (No Session ID)"
    user_or_guest.short_description = "User"

    def price_captured(self, obj):
        if obj.value_at_event:
            return f"৳{obj.value_at_event}"
        return "-"
    price_captured.short_description = "Value"

@admin.register(SearchEvent)
class SearchEventAdmin(admin.ModelAdmin):
    list_display = ('query', 'result_count_badge', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('query',)

    def result_count_badge(self, obj):
        if obj.result_count == 0:
            return format_html('<span class="badge badge-danger">0 Results</span>')
        return obj.result_count
    result_count_badge.short_description = "Found"