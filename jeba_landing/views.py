import json
import random
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db.models import Count, Sum
from django.contrib.admin.views.decorators import staff_member_required

from .models import Campaign, CampaignVariant, VisitorSession, ConversionEvent

from jeba_core.models import SiteSettings

# Helper for Device Detection
def get_device_type(user_agent):
    ua = user_agent.lower()
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        return 'mobile'
    elif 'tablet' in ua or 'ipad' in ua:
        return 'tablet'
    return 'desktop'

def campaign_list(request):
    """
    Shows a list of all active campaigns (offers).
    Replaces the old 'landing_page_list' view.
    """
    campaigns = Campaign.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'jeba_landing/campaign_list.html', {'campaigns': campaigns})

# --- 1. CAMPAIGN DISPATCHER (A/B TESTING CORE) ---

class CampaignDispatchView(View):
    """
    The entry point. Handles:
    1. Looking up the campaign.
    2. Identifying/Creating a Session.
    3. Assigning a Variant (A/B Logic).
    4. Rendering the correct template with the assigned variant.
    """
    def get(self, request, slug):
        campaign = get_object_or_404(Campaign, slug=slug, is_active=True)
        
        # 1. Identify Visitor (Cookie-based)
        session_uuid = request.COOKIES.get('jeba_lid')
        visitor_session = None
        
        if session_uuid:
            visitor_session = VisitorSession.objects.filter(session_uuid=session_uuid, campaign=campaign).first()
            
        # 2. If New Visitor (or cross-campaign), Create Session & Assign Variant
        if not visitor_session:
            # CHECK FOR PREVIEW OVERRIDE
            preview_variant_id = request.GET.get('preview_variant')
            selected_variant = None
            
            if preview_variant_id:
                selected_variant = campaign.variants.filter(id=preview_variant_id).first()
            
            if not selected_variant:
                # A/B Logic: Weighted Random Selection
                variants = list(campaign.variants.all())
                if not variants:
                    return HttpResponse("Campaign Configuration Error: No Variants Found", status=500)
                    
                # Create weighted list
                choices = []
                weights = []
                for v in variants:
                    choices.append(v)
                    weights.append(v.weight)
                    
                # Select
                selected_variant = random.choices(choices, weights=weights, k=1)[0]
            
            # Create Session Record
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            ip = self.get_client_ip(request)
            
            visitor_session = VisitorSession.objects.create(
                campaign=campaign,
                variant=selected_variant,
                ip_address=ip,
                user_agent=user_agent,
                device_type=get_device_type(user_agent),
                utm_source=request.GET.get('utm_source', ''),
                utm_medium=request.GET.get('utm_medium', ''),
                utm_campaign=request.GET.get('utm_campaign', ''),
                referrer_url=request.META.get('HTTP_REFERER', '')
            )
            
            # Log Initial Page View
            ConversionEvent.objects.create(
                session=visitor_session,
                event_type='PAGE_VIEW'
            )

        # 3. Render
        context = {
            'campaign': campaign,
            'variant': visitor_session.variant,
            'sections': visitor_session.variant.sections.all().order_by('order'),
            'session_id': str(visitor_session.session_uuid),
            'product': campaign.product,
            'settings': SiteSettings.load(), # Fix: Pass settings to template
        }
        
        response = render(request, 'jeba_landing/landing_base.html', context)
        
        # Set Cookie (1 Year Expiry)
        if not request.COOKIES.get('jeba_lid') or request.COOKIES.get('jeba_lid') != str(visitor_session.session_uuid):
            response.set_cookie('jeba_lid', str(visitor_session.session_uuid), max_age=31536000, httponly=True, samesite='Lax')
            
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

# --- 2. ANALYTICS API (THE "MONSTER" FEEDER) ---

@method_decorator(csrf_exempt, name='dispatch')
class TrackEventView(View):
    """
    Receives JSON beacons from the frontend.
    Payload: { session_id, event_type, metadata, value }
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            event_type = data.get('event_type')
            
            if not session_id or not event_type:
                return JsonResponse({'error': 'Missing data'}, status=400)
                
            session = VisitorSession.objects.filter(session_uuid=session_id).first()
            if not session:
                return JsonResponse({'error': 'Invalid Session'}, status=404)
                
            ConversionEvent.objects.create(
                session=session,
                event_type=event_type,
                metadata=data.get('metadata', {}),
                value=data.get('value', 0.00)
            )
            
            return JsonResponse({'status': 'ok'})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

# --- 3. DASHBOARD (GOD-TIER REPORTING) ---

@staff_member_required
def analytics_dashboard(request, slug):
    campaign = get_object_or_404(Campaign, slug=slug)
    
    # 1. Headline Metrics
    total_sessions = campaign.sessions.count()
    
    purchases = ConversionEvent.objects.filter(
        session__campaign=campaign, 
        event_type='PURCHASE'
    )
    total_purchases = purchases.count()
    total_revenue = purchases.aggregate(Sum('value'))['value__sum'] or 0.00
    
    conversion_rate = (total_purchases / total_sessions * 100) if total_sessions > 0 else 0
    
    # 2. Variant Performance
    variants_data = []
    for v in campaign.variants.all():
        v_sessions = v.sessions.count()
        v_purchases = ConversionEvent.objects.filter(session__variant=v, event_type='PURCHASE').count()
        v_revenue = ConversionEvent.objects.filter(session__variant=v, event_type='PURCHASE').aggregate(Sum('value'))['value__sum'] or 0
        v_cr = (v_purchases / v_sessions * 100) if v_sessions > 0 else 0
        
        variants_data.append({
            'name': v.name,
            'sessions': v_sessions,
            'purchases': v_purchases,
            'revenue': v_revenue,
            'cr': round(v_cr, 2)
        })

    # 3. Source Breakdown (Where did they come from?)
    sources_query = campaign.sessions.values('utm_source').annotate(count=Count('id')).order_by('-count')
    sources_data = [{'name': s['utm_source'] or 'Direct/None', 'count': s['count']} for s in sources_query[:5]]

    # 4. Detailed Session Log (The "God View")
    # Fetch last 50 sessions with related events to avoid N+1
    recent_sessions = campaign.sessions.prefetch_related('events').order_by('-created_at')[:50]
    
    session_logs = []
    for s in recent_sessions:
        events = s.events.all()
        event_types = [e.event_type for e in events]
        
        # Calculate Duration (Time between first and last event)
        if events.exists():
            duration = (events.last().created_at - events.first().created_at).seconds
        else:
            duration = 0
            
        # Scroll Depth
        scroll = "0%"
        if 'SCROLL_90' in event_types: scroll = "90%"
        elif 'SCROLL_50' in event_types: scroll = "50%"
        
        # Outcome
        outcome = "Bounced"
        row_class = "text-gray-500"
        
        if 'PURCHASE' in event_types: 
            outcome = "💰 PURCHASED"
            row_class = "text-green-600 font-bold bg-green-50"
        elif 'INITIATE_CHECKOUT' in event_types: 
            outcome = "🛒 Checkout"
            row_class = "text-blue-600 font-semibold"
        elif 'ADD_TO_CART' in event_types: 
            outcome = "🛍️ Cart"
        elif duration > 30: 
            outcome = "👀 Reading"
            
        session_logs.append({
            'uuid': str(s.session_uuid)[:8],
            'time': s.created_at,
            'source': s.utm_source or 'Direct',
            'location': f"{s.city}, {s.country}" if s.city else s.country,
            'device': s.device_type,
            'duration': f"{duration}s",
            'scroll': scroll,
            'outcome': outcome,
            'row_class': row_class
        })

    context = {
        'campaign': campaign,
        'summary': {
            'sessions': total_sessions,
            'purchases': total_purchases,
            'revenue': total_revenue,
            'cr': round(conversion_rate, 2)
        },
        'variants': variants_data,
        'sources': sources_data,
        'session_logs': session_logs
    }
    
    return render(request, 'jeba_landing/dashboard.html', context)

# --- 4. ORDER HANDLING ---

from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
import threading
from jeba_inventory.models import Product, ProductVariant
from jeba_core.models import SiteSettings

# Import the Real Sales Models & Services
try:
    from jeba_sales.models import Sale, SaleItem
    from jeba_sales.notifications import send_telegram_order_notification
    from jeba_sales.utils import send_order_email
    from jeba_analytics.utils import send_purchase_event
    from jeba_analytics.analytics_service import AnalyticsService
except ImportError:
    Sale = None

@require_POST
def place_order(request):
    """
    Handles form submission from the landing page.
    Creates a 'Sale' in the inventory system (Standard Checkout Logic).
    Triggers all standard automations: Telegram, CAPI, Email.
    """
    if not Sale:
        messages.error(request, "Sales module not linked.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    product_id = request.POST.get('product_id')
    name = request.POST.get('name')
    phone = request.POST.get('phone')
    address = request.POST.get('address')
    delivery_area = request.POST.get('delivery_area', 'INSIDE') 
    payment_method = request.POST.get('payment_method', 'COD')
    transaction_id = request.POST.get('transaction_id', '').strip()
    
    # Basic Validation
    if payment_method == 'BKASH' and not transaction_id:
        messages.error(request, "Transaction ID is required for bKash payment.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    product = get_object_or_404(Product, id=product_id)
    
    # 0. Stock Check
    if product.stock_quantity <= 0:
        messages.error(request, "Sorry, this product is currently out of stock.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # --- VARIANT HANDLING ---
    final_price = product.selling_price or product.price or 0
    variant_summary_parts = []
    
    # Check for variants in POST (e.g. variant_COLOR, variant_SIZE)
    # The frontend sends: variant_COLOR=123
    variants_to_update = []
    
    for key, value in request.POST.items():
        if key.startswith('variant_') and value:
            try:
                var_id = int(value)
                variant = ProductVariant.objects.get(id=var_id)
                
                # Check Variant Stock
                if variant.stock_quantity <= 0:
                     messages.error(request, f"Sorry, {variant.get_variant_type_display()} '{variant.name}' is out of stock.")
                     return redirect(request.META.get('HTTP_REFERER', '/'))
                
                # Price logic
                final_price += variant.price_adjustment
                
                # Summary logic
                variant_summary_parts.append(f"{variant.get_variant_type_display()}: {variant.name}")
                
                variants_to_update.append(variant)
            except (ValueError, ProductVariant.DoesNotExist):
                continue
                
    variant_summary = ", ".join(variant_summary_parts) if variant_summary_parts else None

    settings_obj = SiteSettings.load()
    
    # Calculate Charge
    delivery_charge = settings_obj.delivery_charge_outside if delivery_area == 'OUTSIDE' else settings_obj.delivery_charge_inside

    try:
        with transaction.atomic():
            # 0. Deduct Stock (Simple Logic)
            # Deduct from main product if no variants tracked, else deduct from variants
            # For this system, we'll deduct main stock regardless for safety, AND variant stock
            if product.stock_quantity > 0:
                product.stock_quantity -= 1
                product.save()
            
            for v in variants_to_update:
                if v.stock_quantity > 0:
                    v.stock_quantity -= 1
                    v.save()

            # 1. Create Sale Record
            new_sale = Sale.objects.create(
                user=request.user if request.user.is_authenticated else None,
                customer_name=name,
                phone_number=phone,
                shipping_address=address,
                status='PENDING',
                delivery_charge=delivery_charge,
                payment_method=payment_method,
                transaction_id=transaction_id if payment_method == 'BKASH' else None
            )
            
            # 2. Create Sale Item
            SaleItem.objects.create(
                sale=new_sale,
                product=product,
                quantity=1,
                sold_price=final_price,
                buying_cost=product.buying_cost or 0,
                variant_summary=variant_summary # <--- NEW FIELD
            )
            
            # 3. Track Conversion (Internal Landing Analytics)
            session_id = request.COOKIES.get('jeba_lid')
            if session_id:
                try:
                    session = VisitorSession.objects.get(session_uuid=session_id)
                    ConversionEvent.objects.create(
                        session=session,
                        event_type='PURCHASE',
                        value=product.selling_price or 0
                    )
                    session.has_converted = True
                    session.save()
                except (VisitorSession.DoesNotExist, ValueError):
                    pass

            # 4. Trigger Post-Purchase Workflows (Async)
            try:
                ip = AnalyticsService.get_client_ip(request)
                ua = request.META.get('HTTP_USER_AGENT', '')
                
                threading.Thread(target=send_telegram_order_notification, args=(new_sale,)).start()
                threading.Thread(target=send_purchase_event, args=(new_sale, ip, ua)).start()
                
                if request.user.is_authenticated and request.user.email:
                    domain_base = request.build_absolute_uri('/')[:-1]
                    tracking_url = f"{domain_base}/track-order/{new_sale.access_token}/"
                    threading.Thread(target=send_order_email, args=(new_sale, request.user.email, tracking_url)).start()
            
            except Exception as task_error:
                print(f"Post-purchase task failed: {task_error}")

            # 5. Set Session for Success Page
            request.session['last_order_id'] = new_sale.id
            request.session['cart'] = {} # Clear main cart to avoid confusion
            
            return redirect('order_success')

    except Exception as e:
        messages.error(request, f"Order failed: {str(e)}")
        return redirect(request.META.get('HTTP_REFERER', '/'))