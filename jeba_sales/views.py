from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
import threading

# --- MODULAR IMPORTS ---
from jeba_inventory.models import Product, ProductVariation
from jeba_sales.models import Sale, SaleItem
from jeba_analytics.models import ProductEvent
from jeba_core.models import SiteSettings
from jeba_analytics.analytics_service import AnalyticsService
# -----------------------

from jeba_sales.forms import CheckoutForm
from jeba_sales.utils import send_order_email, render_to_pdf
from products.steadfast import check_delivery_status
from jeba_analytics.utils import send_purchase_event
# CHANGED: Import the new/updated CAPI functions
from jeba_analytics.utils import send_purchase_event, send_add_to_cart_event

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from django.views.decorators.http import require_POST
from jeba_sales.notifications import send_telegram_order_notification

# --- CART VIEWS ---

def add_to_cart(request: HttpRequest, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if product.call_for_price or product.selling_price <= 0:
        messages.error(request, "Please contact us directly for this product.")
        return redirect('product_detail', pk=product_id)

    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    
    # Check both POST (Form) and GET (Link) for action
    action = request.POST.get('action') or request.GET.get('action')
    
    cart_item_id = str(product_id)

    if cart_item_id in cart:
        # SMART FIX: If 'Buy Now', overwrite quantity. If 'Add to Cart', increment.
        if action == 'buy_now':
            cart[cart_item_id]['quantity'] = quantity
        else:
            cart[cart_item_id]['quantity'] += quantity
    else:
        cart[cart_item_id] = {
            'product_id': product.id,
            'name': product.name,
            'price': float(product.selling_price),
            'quantity': quantity,
            'variation_id': None
        }

    request.session['cart'] = cart
    
    # ANALYTICS (Keep existing code)
    AnalyticsService.track_product_interaction(request, product, 'CART')
    try:
        ip = AnalyticsService.get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
        user = request.user if request.user.is_authenticated else None
        threading.Thread(target=send_add_to_cart_event, args=(product, ip, ua, user)).start()
    except Exception as e:
        print(f"Error triggering ATC Event: {e}")

    if action == 'buy_now':
        return redirect('checkout')
    return redirect('product_detail', pk=product_id)


# 2. UPDATE: Fix 'Buy Now' logic in add_to_cart_variation
def add_to_cart_variation(request: HttpRequest, variation_id):
    variation = get_object_or_404(ProductVariation, id=variation_id)
    product = variation.product
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    action = request.POST.get('action') or request.GET.get('action')

    cart_item_id = f"var_{variation_id}"

    if cart_item_id in cart:
        # SMART FIX: Overwrite if Buy Now
        if action == 'buy_now':
            cart[cart_item_id]['quantity'] = quantity
        else:
            cart[cart_item_id]['quantity'] += quantity
    else:
        cart[cart_item_id] = {
            'product_id': product.id,
            'name': f"{product.name} ({variation.name})",
            'price': float(variation.selling_price),
            'quantity': quantity,
            'variation_id': variation.id
        }

    request.session['cart'] = cart
    
    # ANALYTICS (Keep existing code)
    AnalyticsService.track_product_interaction(request, product, 'CART')
    try:
        ip = AnalyticsService.get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
        user = request.user if request.user.is_authenticated else None
        threading.Thread(target=send_add_to_cart_event, args=(product, ip, ua, user)).start()
    except Exception as e:
        print(f"Error triggering ATC Event: {e}")

    if action == 'buy_now':
        return redirect('checkout')
    return redirect('product_detail', pk=product.id)


def view_cart(request):
    """
    Displays the cart. 
    FIX: Re-added logic to fetch 'Product' objects so the template can show images.
    """
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0

    for key, item_data in cart.items():
        try:
            product = Product.objects.get(id=item_data['product_id'])
        except Product.DoesNotExist:
            continue

        # Fetch Variation if exists
        variation = None
        if item_data.get('variation_id'):
            try:
                variation = ProductVariation.objects.get(id=item_data['variation_id'])
            except ProductVariation.DoesNotExist:
                pass

        item_total = item_data['price'] * item_data['quantity']
        is_call_for_price = product.call_for_price or product.selling_price <= 0

        # Build the object expected by the template
        cart_items.append({
            'id': key,
            'product': product,       # <--- This was missing! Template needs this for images.
            'variation': variation,
            'name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity'],
            'item_total': item_total,
            'call_for_price': is_call_for_price,
        })
        
        if not is_call_for_price:
            total_price += item_total

    settings_obj = SiteSettings.load()
    context = {
        'cart_items': cart_items, # <--- Template iterates over this
        'total_price': total_price,
        'delivery_inside': settings_obj.delivery_charge_inside,
        'delivery_outside': settings_obj.delivery_charge_outside
    }
    return render(request, 'jeba_sales/view_cart.html', context)


def update_cart(request, item_id, action):
    cart = request.session.get('cart', {})
    
    if item_id in cart:
        item = cart[item_id]
        
        if action == 'increase':
            product_id = item['product_id']
            variation_id = item.get('variation_id')
            product = get_object_or_404(Product, id=product_id)
            current_qty = item['quantity']
            
            stock_ok = True
            if variation_id:
                try:
                    variation = ProductVariation.objects.get(id=variation_id)
                    if variation.stock_quantity <= current_qty: stock_ok = False
                except ProductVariation.DoesNotExist: stock_ok = False
            else:
                if product.stock_quantity <= current_qty: stock_ok = False
            
            if stock_ok:
                cart[item_id]['quantity'] += 1
            else:
                messages.warning(request, "Maximum stock reached.")
                
        elif action == 'decrease':
            cart[item_id]['quantity'] -= 1
            if cart[item_id]['quantity'] < 1:
                del cart[item_id]
                
        elif action == 'remove':
            del cart[item_id]
    
    request.session['cart'] = cart
    return redirect('view_cart')

# --- ADD THIS NEW VIEW FUNCTION ---
@require_POST
def update_cart_api(request):
    """
    AJAX Endpoint to update cart quantity or remove items.
    Returns JSON with new totals to update the DOM without refresh.
    """
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        action = data.get('action')
        
        if not item_id or not action:
            return JsonResponse({'status': 'error', 'message': 'Invalid parameters'}, status=400)

        cart = request.session.get('cart', {})
        
        if item_id not in cart:
             return JsonResponse({'status': 'error', 'message': 'Item not found in cart'}, status=404)
             
        item = cart[item_id]
        current_qty = item['quantity']
        
        # Logic matches your existing update_cart checks
        if action == 'increase':
            product_id = item['product_id']
            variation_id = item.get('variation_id')
            
            # Stock Check
            stock_ok = True
            product = Product.objects.get(id=product_id) # Simplify for speed, add error handling in prod
            
            if variation_id:
                try:
                    variation = ProductVariation.objects.get(id=variation_id)
                    if variation.stock_quantity <= current_qty: stock_ok = False
                except ProductVariation.DoesNotExist: stock_ok = False
            else:
                if product.stock_quantity <= current_qty: stock_ok = False
                
            if stock_ok:
                cart[item_id]['quantity'] += 1
            else:
                return JsonResponse({'status': 'error', 'message': 'Maximum stock reached'}, status=400)

        elif action == 'decrease':
            cart[item_id]['quantity'] -= 1
            if cart[item_id]['quantity'] < 1:
                del cart[item_id]
                
        elif action == 'remove':
            del cart[item_id]

        request.session['cart'] = cart
        
        # Calculate new totals
        new_cart_total = 0
        new_item_total = 0
        new_item_qty = 0
        cart_count = len(cart)
        
        for key, val in cart.items():
            line_total = val['price'] * val['quantity']
            new_cart_total += line_total
            if key == item_id:
                new_item_total = line_total
                new_item_qty = val['quantity']

        return JsonResponse({
            'status': 'success',
            'cart_total': new_cart_total,
            'item_total': new_item_total,
            'item_qty': new_item_qty,
            'cart_count': cart_count,
            'action_performed': action
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# --- CHECKOUT & ORDERS ---


def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect('view_cart')
    
    settings_obj = SiteSettings.load()
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Lock & Check Stock
                    for key, item_data in cart.items():
                        product_id = item_data['product_id']
                        variation_id = item_data.get('variation_id')
                        order_qty = item_data['quantity']

                        product = Product.objects.select_for_update().get(id=product_id)
                        
                        if product.stock_quantity < order_qty:
                            raise ValueError(f"Sorry, '{product.name}' is out of stock. Only {product.stock_quantity} left.")

                        if variation_id:
                            variation = ProductVariation.objects.select_for_update().get(id=variation_id)
                            if variation.stock_quantity < order_qty:
                                raise ValueError(f"Sorry, '{product.name} - {variation.name}' is out of stock. Only {variation.stock_quantity} left.")

                    # 2. Create Sale
                    new_sale = form.save(commit=False)
                    if request.user.is_authenticated:
                        new_sale.user = request.user

                    delivery_area = form.cleaned_data.get('delivery_area')
                    if delivery_area == 'OUTSIDE':
                        new_sale.delivery_charge = settings_obj.delivery_charge_outside
                    else:
                        new_sale.delivery_charge = settings_obj.delivery_charge_inside
                    
                    new_sale.save()

                    # 3. Create Items & Track Event
                    for key, item_data in cart.items():
                        product = Product.objects.get(id=item_data['product_id'])
                        variation = None
                        if item_data.get('variation_id'):
                            variation = ProductVariation.objects.get(id=item_data['variation_id'])
                        
                        SaleItem.objects.create(
                            sale=new_sale,
                            product=product,
                            variation=variation,
                            quantity=item_data['quantity'],
                            sold_price=item_data['price'],
                            buying_cost=product.buying_cost 
                        )
                        
                        AnalyticsService.track_product_interaction(request, product, 'PURCHASE')
                
                # --- UPDATED: SEND PURCHASE EVENT CORRECTLY ---
                try:
                    ip = AnalyticsService.get_client_ip(request)
                    ua = request.META.get('HTTP_USER_AGENT', '')
                    
                    # Pass strings (IP, UA) instead of request object to avoid threading issues
                    threading.Thread(
                        target=send_purchase_event, 
                        args=(new_sale, ip, ua)
                    ).start()
                except Exception as e:
                    print(f"Error starting CAPI thread: {e}")
                # ----------------------------------------------
                # --- ASYNC NOTIFICATIONS (Non-blocking) ---
                try:
                    ip = AnalyticsService.get_client_ip(request)
                    ua = request.META.get('HTTP_USER_AGENT', '')
                    
                    # 1. CAPI Event
                    threading.Thread(
                        target=send_purchase_event, 
                        args=(new_sale, ip, ua)
                    ).start()
                    
                    # 2. Telegram Notification (NEW)
                    threading.Thread(
                        target=send_telegram_order_notification,
                        args=(new_sale,)
                    ).start()

                except Exception as e:
                    print(f"Error starting background threads: {e}")
                # ----------------------------------------------
                request.session['last_order_id'] = new_sale.id

                if request.user.is_authenticated and request.user.email:
                    domain_base = request.build_absolute_uri('/')[:-1]
                    tracking_url = f"{domain_base}/track-order/{new_sale.access_token}/"
                    
                    email_thread = threading.Thread(
                        target=send_order_email, 
                        args=(new_sale, request.user.email, tracking_url) 
                    )
                    email_thread.start()

                request.session['cart'] = {}
                return redirect('order_success')

            except ValueError as e:
                messages.error(request, str(e))
                return redirect('view_cart')
            except Exception as e:
                print(f"Checkout Error: {e}")
                messages.error(request, "An unexpected error occurred. Please try again.")
                return redirect('view_cart')
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data['customer_name'] = f"{request.user.first_name} {request.user.last_name}".strip()
            if hasattr(request.user, 'profile'):
                initial_data['phone_number'] = request.user.profile.phone_number
                initial_data['shipping_address'] = request.user.profile.address
        form = CheckoutForm(initial=initial_data)

    # Build cart items for display in checkout
    cart_items = []
    total_price = 0
    for key, item_data in cart.items():
        try:
            product = Product.objects.get(id=item_data['product_id'])
        except Product.DoesNotExist:
            continue
            
        variation = None
        if item_data.get('variation_id'):
            try:
                variation = ProductVariation.objects.get(id=item_data['variation_id'])
            except ProductVariation.DoesNotExist:
                pass

        item_total = item_data['price'] * item_data['quantity']
        
        cart_items.append({
            'id': key, # <--- ADDED THIS LINE (Critical for AJAX)
            'product': product,
            'variation': variation,
            'name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity'],
            'item_total': item_total,
        })
        total_price += item_total

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'form': form,
        'settings': settings_obj,
    }
    return render(request, 'jeba_sales/checkout.html', context)

def order_success(request):
    last_order_id = request.session.get('last_order_id')
    sale = None
    if last_order_id:
        sale = Sale.objects.filter(id=last_order_id).prefetch_related('items').first()
        
    return render(request, 'jeba_sales/order_success.html', {'sale': sale})

@login_required
def my_orders_view(request):
    user_orders = Sale.objects.filter(user=request.user).order_by('-created_at').prefetch_related('items')

    for order in user_orders:
        if order.consignment_id and order.status not in ['DELIVERED', 'CANCELLED']:
            try:
                api_status = check_delivery_status(order.consignment_id, invoice_number=order.invoice_number)
                
                if api_status and api_status != 'unknown':
                    if api_status in ['delivered', 'partial_delivered']:
                        if order.status != 'DELIVERED':
                            order.status = 'DELIVERED'
                            order.save(update_fields=['status'])
                    elif api_status == 'cancelled':
                        if order.status != 'CANCELLED':
                            order.status = 'CANCELLED'
                            order.save(update_fields=['status'])
            except Exception as e:
                print(f"Error syncing order {order.id}: {e}")

    context = {
        'orders': user_orders
    }
    return render(request, 'jeba_accounts/registration/my_orders.html', context)

@login_required
def order_detail(request, pk):
    sale = get_object_or_404(Sale.objects.prefetch_related('items'), pk=pk)
    
    if sale.user != request.user:
        return redirect('my_orders')

    live_status = None
    if sale.consignment_id:
        live_status = check_delivery_status(sale.consignment_id, invoice_number=sale.invoice_number)
    
    context = {
        'sale': sale,
        'live_status': live_status 
    }
    return render(request, 'jeba_sales/order_detail.html', context)

def guest_order_track(request, token):
    sale = get_object_or_404(Sale.objects.prefetch_related('items'), access_token=token)
    
    live_status = None
    if sale.consignment_id:
        try:
            live_status = check_delivery_status(sale.consignment_id, invoice_number=sale.invoice_number)
            if live_status:
                if live_status == 'delivered' and sale.status != 'DELIVERED':
                    sale.status = 'DELIVERED'
                    sale.save(update_fields=['status'])
                elif live_status == 'cancelled' and sale.status != 'CANCELLED':
                    sale.status = 'CANCELLED'
                    sale.save(update_fields=['status'])
        except:
            pass

    context = {
        'sale': sale,
        'live_status': live_status,
        'is_guest_view': True,
        'progress_width': 0 # Placeholder
    }
    return render(request, 'jeba_sales/order_detail.html', context)

def order_receipt(request, token):
    sale = get_object_or_404(Sale, access_token=token)
    domain = request.build_absolute_uri('/')[:-1]
    tracking_url = f"{domain}/track-order/{sale.access_token}/"
    
    context = {
        'sale': sale,
        'tracking_url': tracking_url,
        'settings': SiteSettings.load()
    }
    return render(request, 'jeba_sales/receipt.html', context)

def download_invoice_pdf(request, token):
    sale = get_object_or_404(Sale, access_token=token)
    domain = request.build_absolute_uri('/')[:-1]
    tracking_url = f"{domain}/track-order/{sale.access_token}/"
    
    data = {
        'sale': sale,
        'tracking_url': tracking_url,
        'settings': SiteSettings.load(),
    }
    
    pdf_bytes = render_to_pdf('jeba_sales/invoice_pdf.html', data)
    
    if pdf_bytes:
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Invoice_{sale.invoice_number}.pdf"
        response['Content-Disposition'] = f"attachment; filename={filename}"
        return response
    
    return HttpResponse("Not found", status=404)

@csrf_exempt
def steadfast_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    try:
        payload = json.loads(request.body)
        consignment_id = payload.get('consignment_id')
        
        if not consignment_id:
            return JsonResponse({'status': 'error', 'message': 'Missing consignment_id'}, status=400)

        try:
            sale = Sale.objects.get(consignment_id=consignment_id)
        except Sale.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid consignment ID.'}, status=404)

        notification_type = payload.get('type')
        if notification_type == 'delivery_status':
            new_status = payload.get('status', '').lower()
            
            status_map = {
                'delivered': 'DELIVERED',
                'partial_delivered': 'DELIVERED', 
                'cancelled': 'CANCELLED',
                'pending': 'PENDING',
                'in_review': 'PROCESSING'
            }
            
            if new_status in status_map:
                sale.status = status_map[new_status]
                sale.save(update_fields=['status'])

        return JsonResponse({'status': 'success', 'message': 'Webhook received successfully.'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)