from django.contrib import admin
from django.db.models import Count, Q, Sum, F, ExpressionWrapper, DecimalField, Avg
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta

# --- MODELS ---
from .models import ProductEvent, SearchEvent, DailyAdSpend
from jeba_inventory.models import Product
from jeba_sales.models import SaleItem
import json
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import SessionTrace, SearchEvent, ProductEvent, DailyAdSpend
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Avg, Case, When, Value

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
    # --- ADD THIS LINE TO FIX THE ERROR ---
    readonly_fields = ('total_revenue', 'total_profit', 'total_orders')
    # --------------------------------------
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
    
    list_display = (
        'name', 
        'funnel_visual',
        'engagement_stats',
        'view_to_cart_rate',
        'cart_abandonment', 
        'sales_conversion', 
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
            avg_time=Avg('events__time_on_page', filter=Q(events__event_type='VIEW')),
            avg_scroll=Avg('events__scroll_depth', filter=Q(events__event_type='VIEW')),
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

    # --- NEW: CALCULATE GRAND TOTALS FOR TOP CARDS ---
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        
        # Only calculate if we are returning a TemplateResponse (not a redirect/JSON)
        if hasattr(response, 'context_data'):
            qs = self.get_queryset(request)
            
            # Aggregate data across ALL products
            metrics = qs.aggregate(
                grand_revenue=Sum('total_revenue'),
                grand_cost=Sum('total_cost'),
                grand_views=Sum('views'),
                grand_orders=Sum('orders')
            )
            
            grand_revenue = metrics['grand_revenue'] or 0
            grand_cost = metrics['grand_cost'] or 0
            grand_profit = grand_revenue - grand_cost
            
            grand_views = metrics['grand_views'] or 0
            grand_orders = metrics['grand_orders'] or 0
            
            global_conversion = 0
            if grand_views > 0:
                global_conversion = (grand_orders / grand_views) * 100

            # Pass to template
            response.context_data['summary_metrics'] = {
                'total_profit': grand_profit,
                'conversion_rate': round(global_conversion, 2),
                'total_revenue': grand_revenue,
                'total_views': grand_views
            }
            
        return response

    # --- METRICS DISPLAY (Same as before) ---
    def engagement_stats(self, obj):
        time_sec = int(obj.avg_time or 0)
        scroll_pct = int(obj.avg_scroll or 0)
        scroll_color = "green" if scroll_pct > 50 else "orange" if scroll_pct > 25 else "red"
        return format_html(
            '''<div style="font-size: 12px;">⏱️ <b>{m}m {s}s</b><br>
            📜 <span style="color:{sc}">{scroll}% Read</span></div>''',
            m=time_sec // 60, s=time_sec % 60, scroll=scroll_pct, sc=scroll_color
        )
    engagement_stats.short_description = "Avg Engagement"

    def funnel_visual(self, obj):
        views = obj.views or 0
        carts = obj.carts or 0
        orders = obj.orders or 0
        if views == 0: return "-"
        cart_pct = min(100, int((carts / views) * 100))
        order_pct = min(100, int((orders / views) * 100))
        return format_html(
            '''<div style="min-width: 150px;">
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
            </div>''', v=views, c=carts, o=orders, cp=cart_pct, op=order_pct
        )
    funnel_visual.short_description = "Funnel"

    def view_to_cart_rate(self, obj):
        if obj.views == 0: return "-"
        rate = (obj.carts / obj.views) * 100
        color = "red" if rate < 2 else "green"
        return format_html(f"<span style='color:{color}; font-weight:bold;'>{rate:.1f}%</span>")
    view_to_cart_rate.short_description = "Add-to-Cart %"
    view_to_cart_rate.admin_order_field = 'carts'

    def cart_abandonment(self, obj):
        if obj.carts == 0: return "-"
        abandoned_carts = obj.carts - obj.orders
        rate = (abandoned_carts / obj.carts) * 100
        color = "red" if rate > 70 else "orange" if rate > 50 else "green"
        return format_html(f"<span style='color:{color}; font-weight:bold;'>{rate:.1f}%</span>")
    cart_abandonment.short_description = "Abandonment %"

    def sales_conversion(self, obj):
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
    list_display = (
        'product', 
        'event_type', 
        'attribution_display', # NEW
        'behavior_display',    # NEW
        'user_or_guest', 
        'created_at'
    )
    list_filter = (
        'event_type', 
        'utm_source',     # NEW: Filter by Ad Source
        'stock_status_at_view', 
        'created_at'
    )
    search_fields = ('product__name', 'session_id', 'utm_source', 'utm_campaign')
    readonly_fields = ('created_at', 'session_id', 'metadata')
    
    def user_or_guest(self, obj):
        if obj.user:
            return obj.user.username
        if obj.session_id:
            return f"Guest ({obj.session_id[:8]}...)"
        return "Guest"
    user_or_guest.short_description = "User"

    def attribution_display(self, obj):
        """Shows marketing source."""
        source = obj.utm_source or "-"
        medium = obj.utm_medium or ""
        if source == "-": return "-"
        return f"{source} / {medium}"
    attribution_display.short_description = "Source / Medium"

    def behavior_display(self, obj):
        """Shows Time & Scroll."""
        if obj.event_type != 'VIEW': return "-"
        
        time_str = f"{obj.time_on_page}s" if obj.time_on_page else "0s"
        scroll_str = f"{obj.scroll_depth}%" if obj.scroll_depth else "0%"
        
        # Highlight high engagement
        if obj.time_on_page > 60:
            return format_html(f"<span style='color:green; font-weight:bold'>{time_str} | {scroll_str}</span>")
        return f"{time_str} | {scroll_str}"
    behavior_display.short_description = "Time | Scroll"


# --- HELPERS ---
def pretty_json(data):
    """Format JSON for readability in Admin."""
    try:
        return format_html(
            '<pre style="background: #2d2d2d; color: #ccc; padding: 10px; border-radius: 5px; overflow-x: auto;">{}</pre>',
            json.dumps(data, indent=2, sort_keys=True)
        )
    except Exception:
        return data

@admin.register(SessionTrace)
class SessionTraceAdmin(admin.ModelAdmin):
    list_display = (
        'short_session_id', 
        'device_badge', 
        'network_status',
        'load_time_display', 
        'scroll_depth_bar', 
        'is_bounce_badge', 
        'created_at'
    )
    list_filter = (
        'is_bounce', 
        'device_type', 
        ('created_at', admin.DateFieldListFilter),
        'load_time_ms' # Useful if you have a range filter installed, otherwise standard
    )
    search_fields = ('session_id', 'url', 'ip_address')
    # --- CRITICAL FIX: Add created_at to readonly_fields ---
    readonly_fields = ('session_id', 'formatted_raw_data', 'performance_breakdown', 'created_at')
    # --- VISUAL DASHBOARD INJECTION ---
    change_list_template = "admin/jeba_analytics/sessiontrace/change_list.html"

    def changelist_view(self, request, extra_context=None):
        # 1. Aggregate Data from the Queryset
        # FIX: We fetch IDs first to avoid "Cannot filter a sliced queryset" error
        last_1000_ids = list(SessionTrace.objects.order_by('-created_at').values_list('id', flat=True)[:1000])
        
        if not last_1000_ids:
            dashboard_data = {
                'total_sessions': 0,
                'bounce_rate': 0,
                'avg_load_time': 0,
                'devices': '[]',
                'speed_stats': '{"fast": 0, "slow": 0}',
            }
        else:
            # Create a new, clean queryset based on these IDs
            qs = SessionTrace.objects.filter(id__in=last_1000_ids)
            
            # A. Bounce Rate
            total = qs.count()
            bounces = qs.filter(is_bounce=True).count()
            bounce_rate = round((bounces / total * 100), 1) if total > 0 else 0
            
            # B. Average Load Time (Avg of 'fullLoad')
            avg_load = qs.aggregate(Avg('load_time_ms'))['load_time_ms__avg'] or 0
            
            # C. Device Breakdown
            devices = list(qs.values('device_type').annotate(count=Count('device_type')))
            
            # D. Network Performance (Fast vs Slow)
            speed_stats = qs.aggregate(
                fast=Count(Case(When(load_time_ms__lt=2000, then=1))),
                slow=Count(Case(When(load_time_ms__gte=2000, then=1)))
            )

            dashboard_data = {
                'total_sessions': total,
                'bounce_rate': bounce_rate,
                'avg_load_time': round(avg_load),
                'devices': json.dumps(devices, cls=DjangoJSONEncoder),
                'speed_stats': json.dumps(speed_stats, cls=DjangoJSONEncoder),
            }

        extra_context = extra_context or {}
        extra_context.update(dashboard_data)
        
        return super().changelist_view(request, extra_context=extra_context)

    fieldsets = (
        ("Session Identity", {
            "fields": ("session_id", "url", "created_at", "ip_address")
        }),
        ("Device & Network", {
            "fields": ("user_agent", "device_type")
        }),
        ("Performance Metrics", {
            "fields": ("load_time_ms", "ttfb_ms", "performance_breakdown")
        }),
        ("Engagement", {
            "fields": ("duration_ms", "max_scroll", "is_bounce")
        }),
        ("The Black Box", {
            "fields": ("formatted_raw_data",),
            "classes": ("collapse",),
        }),
    )

    def short_session_id(self, obj):
        return obj.session_id[:8] + "..."
    short_session_id.short_description = "ID"

    def device_badge(self, obj):
        icons = {
            'mobile': 'fa-mobile-alt',
            'desktop': 'fa-desktop',
            'tablet': 'fa-tablet-alt'
        }
        icon = icons.get(obj.device_type, 'fa-question')
        return format_html(f'<i class="fas {icon}"></i> {obj.device_type}')
    device_badge.short_description = "Device"

    def network_status(self, obj):
        # Infer network quality from TTFB
        if not obj.ttfb_ms: return "-"
        
        if obj.ttfb_ms < 100:
            color = "#00c853" # Green (Fast/WiFi)
            label = "⚡ 5G/WiFi"
        elif obj.ttfb_ms < 300:
            color = "#ffab00" # Orange (4G)
            label = "📶 4G"
        else:
            color = "#d50000" # Red (3G/Slow)
            label = "🐌 Slow 3G"
            
        return format_html(f'<span style="color: {color}; font-weight: bold;">{label}</span>')
    network_status.short_description = "Est. Network"

    def load_time_display(self, obj):
        if not obj.load_time_ms:
            return "-"
        
        # Color scale for Load Time
        val = obj.load_time_ms
        if val < 1500: color = "green"
        elif val < 3500: color = "orange"
        else: color = "red"
        
        return format_html(
            f'<span style="color: {color}; font-weight: bold;">{val}ms</span>'
        )
    load_time_display.short_description = "Load Time"

    def scroll_depth_bar(self, obj):
        # Visual progress bar for scroll
        percent = min(obj.max_scroll, 100)
        color = "#007bff" if percent > 50 else "#6c757d"
        return format_html(
            f'<div style="width: 100px; background: #e9ecef; border-radius: 3px;">'
            f'<div style="width: {percent}%; background: {color}; height: 5px; border-radius: 3px;"></div>'
            f'</div>'
        )
    scroll_depth_bar.short_description = "Scroll"

    def is_bounce_badge(self, obj):
        if obj.is_bounce:
            return format_html('<span style="color: red;">❌ Bounce</span>')
        return format_html('<span style="color: green;">✅ Engaged</span>')
    is_bounce_badge.short_description = "Status"

    def formatted_raw_data(self, obj):
        return pretty_json(obj.raw_data)
    formatted_raw_data.short_description = "Full Telemetry JSON"

    def performance_breakdown(self, obj):
        """Extracts and formats performance object specifically."""
        perf = obj.raw_data.get('performance', {})
        return pretty_json(perf)
    performance_breakdown.short_description = "Timing Breakdown"

@admin.register(SearchEvent)
class SearchEventAdmin(admin.ModelAdmin):
    list_display = ('query', 'result_count_badge', 'attribution_display', 'user', 'created_at')
    list_filter = ('created_at', 'utm_source')
    search_fields = ('query', 'utm_source')

    def result_count_badge(self, obj):
        if obj.result_count == 0:
            return format_html('<span class="badge badge-danger" style="color:red; font-weight:bold;">0 Results</span>')
        return obj.result_count
    result_count_badge.short_description = "Found"

    def attribution_display(self, obj):
        if not obj.utm_source: return "-"
        return f"{obj.utm_source}"
    attribution_display.short_description = "Source"