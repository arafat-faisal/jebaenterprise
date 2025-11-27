import json
import os
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, F
from django.db.models.functions import TruncDate

# Import models
from jeba_sales.models import Sale, SaleItem
from jeba_analytics.models import DailyAdSpend, ProductEvent, SearchEvent

try:
    import geoip2.database
except ImportError:
    geoip2 = None

class AnalyticsService:
    """
    Central intelligence engine for extracting user context and calculating financial KPIs.
    """

    # --- 1. USER CONTEXT & GEOLOCATION ---
    @staticmethod
    def get_client_ip(request):
        """Smart extraction of IP address handling proxies/Cloudflare."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def get_device_info(request):
        """Parses User-Agent to determine device type."""
        ua_string = request.META.get('HTTP_USER_AGENT', '').lower()
        if 'tablet' in ua_string or 'ipad' in ua_string:
            return 'tablet'
        elif 'mobile' in ua_string or 'iphone' in ua_string or 'android' in ua_string:
            return 'mobile'
        return 'desktop'

    @classmethod
    def get_location_from_ip(cls, ip):
        """Resolves IP to City/Country using GeoIP2."""
        if not geoip2:
            return {'city': None, 'country': None}
        
        # Adjust path to your actual GeoLite2 file location if different
        db_path = os.path.join(settings.BASE_DIR, 'geoip', 'GeoLite2-City.mmdb')
        
        try:
            if not os.path.exists(db_path):
                return {'city': None, 'country': None, 'error': 'DB missing'}

            with geoip2.database.Reader(db_path) as reader:
                response = reader.city(ip)
                return {
                    'city': response.city.name,
                    'country': response.country.name,
                    'iso_code': response.country.iso_code
                }
        except Exception:
            return {'city': None, 'country': None}

    # --- 2. EVENT TRACKING ---
    @classmethod
    def track_product_interaction(cls, request, product, event_type):
        """
        Records a product interaction (View, Cart, Purchase) with context.
        """
        ip = cls.get_client_ip(request)
        device = cls.get_device_info(request)
        
        # Capture context metadata
        meta = {
            'ip': ip,
            'device': device,
            'referer': request.META.get('HTTP_REFERER', ''),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200]
        }

        ProductEvent.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key,
            event_type=event_type,
            value_at_event=product.selling_price, # Capture price at this moment
            metadata=meta
        )

    @classmethod
    def track_search(cls, request, query, result_count=0):
        """
        Records internal search queries to analyze user intent.
        """
        if not query:
            return
            
        SearchEvent.objects.create(
            query=query[:255],
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key,
            result_count=result_count,
            metadata={'ip': cls.get_client_ip(request)}
        )

    # --- 3. FINANCIAL INTELLIGENCE (The Brain) ---
    @staticmethod
    def calculate_profit_kpis(days=30):
        """
        Generates the 'True Profit' report by merging Sales Data with Ad Spend.
        Returns a summary dictionary and a daily breakdown list.
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # 1. Fetch Ad Spend for the period
        ad_spends = DailyAdSpend.objects.filter(date__range=(start_date, end_date))
        spend_map = {obj.date: obj for obj in ad_spends}

        # 2. Aggregate Sales Data by Date
        # Only count valid sales (Processing, Shipped, Delivered)
        # Exclude Pending/Cancelled to avoid false profit reporting
        sales_data = (
            SaleItem.objects
            .filter(
                sale__created_at__date__range=(start_date, end_date),
                sale__status__in=['PROCESSING', 'SHIPPED', 'DELIVERED']
            )
            .annotate(date=TruncDate('sale__created_at'))
            .values('date')
            .annotate(
                revenue=Sum(F('sold_price') * F('quantity')),
                cost=Sum(F('buying_cost') * F('quantity')),
                items_sold=Sum('quantity')
            )
            .order_by('-date')
        )

        # 3. Merge & Calculate Net Profit
        daily_stats = []
        total_revenue = Decimal(0)
        total_cogs = Decimal(0) # Cost of Goods Sold
        total_ad_spend = Decimal(0)

        # Iterate backwards from today
        current_date = end_date
        while current_date >= start_date:
            # Get sales data for this date (if any)
            day_sales = next((item for item in sales_data if item['date'] == current_date), {})
            
            revenue = day_sales.get('revenue', Decimal(0))
            cogs = day_sales.get('cost', Decimal(0))
            items = day_sales.get('items_sold', 0)
            
            # Get ad spend for this date (if any)
            spend_obj = spend_map.get(current_date)
            ad_spend = spend_obj.total_spend if spend_obj else Decimal(0)

            # --- THE CORE FORMULA ---
            gross_profit = revenue - cogs
            net_profit = gross_profit - ad_spend
            
            # Return on Ad Spend (ROAS)
            roas = round((revenue / ad_spend), 2) if ad_spend > 0 else 0
            
            # Update Grand Totals
            total_revenue += revenue
            total_cogs += cogs
            total_ad_spend += ad_spend

            daily_stats.append({
                'date': current_date,
                'revenue': revenue,
                'cogs': cogs,
                'ad_spend': ad_spend,
                'net_profit': net_profit,
                'items_sold': items,
                'roas': roas
            })
            
            current_date -= timedelta(days=1)

        # 4. Final Aggregates
        grand_gross_profit = total_revenue - total_cogs
        grand_net_profit = grand_gross_profit - total_ad_spend
        
        profit_margin = 0
        if total_revenue > 0:
            profit_margin = round((grand_net_profit / total_revenue * 100), 2)

        return {
            'summary': {
                'total_revenue': total_revenue,
                'total_ad_spend': total_ad_spend,
                'total_net_profit': grand_net_profit,
                'profit_margin': profit_margin
            },
            'daily_breakdown': daily_stats
        }