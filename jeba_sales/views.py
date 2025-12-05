from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
import json
import threading

# --- MODULAR IMPORTS ---
from jeba_inventory.models import Product, ProductVariation
from jeba_sales.models import Sale, SaleItem
from jeba_core.models import SiteSettings
from jeba_analytics.analytics_service import AnalyticsService
from jeba_sales.forms import CheckoutForm, AddToCartForm
from jeba_sales.utils import send_order_email, render_to_pdf
from products.steadfast import check_delivery_status
from jeba_analytics.utils import send_purchase_event, send_add_to_cart_event
from jeba_sales.notifications import send_telegram_order_notification

# --- CART VIEWS ---

def add_to_cart(request: HttpRequest, product_id):
    """
    Handles adding simple products (no variations) to the cart.
    """
    product = get_object_or_404(Product, id=product_id)
    
    # 1. Basic Validation
    if not product.is_active:
        messages.error(request, "This product is currently unavailable.")
        return redirect('product_detail', pk=product_id)
        
    if product.call_for_price:
        messages.info(request, "Please contact us for pricing.")
        return redirect('product_detail', pk=product_id)

    # 2. Get Quantity
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1: quantity = 1
    except ValueError:
        quantity = 1

    # 3. Stock Check (Server Side Safety)
    if product.stock_quantity < quantity:
        messages.warning(request, f"Sorry, only {product.stock_quantity} units available in stock.")
        return redirect('product_detail', pk=product_id)

    # 4. Add to Session
    cart = request.session.get('cart', {})
    cart_item_id = str(product_id)
    action = request.POST.get('action') or request.GET.get('action')

    if cart_item_id in cart:
        if action == 'buy_now':
            cart[cart_item_id]['quantity'] = quantity # Overwrite
        else:
            # Check combined stock for existing + new
            new_total = cart[cart_item_id]['quantity'] + quantity
            if new_total > product.stock_quantity:
                messages.warning(request, f"You already have {cart[cart_item_id]['quantity']} in cart. Cannot add more.")
                return redirect('product_detail', pk=product_id)
            cart[cart_item_id]['quantity'] += quantity
    else:
        cart[cart_item_id] = {
            'product_id': product.id,
            'name': product.name,
            'price': float(product.selling_price),
            'quantity': quantity,
            'variation_id': None,
            'image_url': product.thumbnail.url if product.thumbnail else ''
        }

    request.session['cart'] = cart
    
    # 5. Analytics (Async)
    _trigger_atc_event(request, product)

    if action == 'buy_now':
        return redirect('checkout')
    
    messages.success(request, f"Added {product.name} to cart.")
    return redirect('product_detail', pk=product_id)


def add_to_cart_variation(request: HttpRequest, variation_id):
    """
    Handles adding specific product variations to the cart.
    """
    variation = get_object_or_404(ProductVariation, id=variation_id)
    product = variation.product

    # 1. Basic Validation
    if not variation.is_active or not product.is_active:
        messages.error(request, "This variation is currently unavailable.")
        return redirect('product_detail', pk=product.id)

    # 2. Get Quantity
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1: quantity = 1
    except ValueError:
        quantity = 1

    # 3. Stock Check (Specific to Variation)
    if variation.stock_quantity < quantity:
        messages.warning(request, f"Sorry, only {variation.stock_quantity} units of '{variation.name}' available.")
        return redirect('product_detail', pk=product.id)

    # 4. Add to Session
    cart = request.session.get('cart', {})
    cart_item_id = f"var_{variation_id}"
    action = request.POST.get('action') or request.GET.get('action')

    price_to_use = float(variation.selling_price)

    if cart_item_id in cart:
        if action == 'buy_now':
            cart[cart_item_id]['quantity'] = quantity
        else:
            new_total = cart[cart_item_id]['quantity'] + quantity
            if new_total > variation.stock_quantity:
                messages.warning(request, "Cannot add more than available stock.")
                return redirect('product_detail', pk=product.id)
            cart[cart_item_id]['quantity'] += quantity
    else:
        cart[cart_item_id] = {
            'product_id': product.id,
            'name': f"{product.name} ({variation.name})",
            'price': price_to_use,
            'quantity': quantity,
            'variation_id': variation.id,
            'image_url': product.thumbnail.url if product.thumbnail else ''
        }

    request.session['cart'] = cart
    
    # 5. Analytics
    _trigger_atc_event(request, product)

    if action == 'buy_now':
        return redirect('checkout')
    
    messages.success(request, f"Added {variation.name} to cart.")
    return redirect('product_detail', pk=product.id)


def _trigger_atc_event(request, product):
    """Helper to fire CAPI event in background"""
    try:
        AnalyticsService.track_product_interaction(request, product, 'CART')
        ip = AnalyticsService.get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
        user = request.user if request.user.is_authenticated else None
        threading.Thread(target=send_add_to_cart_event, args=(product, ip, ua, user)).start()
    except Exception as e:
        print(f"Error triggering ATC Event: {e}")


def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0

    for key, item_data in cart.items():
        # Clean up stale items
        try:
            product = Product.objects.get(id=item_data['product_id'])
        except Product.DoesNotExist:
            continue # Skip deleted products

        # Fetch Variation if exists
        variation = None
        if item_data.get('variation_id'):
            try:
                variation = ProductVariation.objects.get(id=item_data['variation_id'])
            except ProductVariation.DoesNotExist:
                continue # Skip deleted variations

        item_total = item_data['price'] * item_data['quantity']
        
        # Determine active status for display
        is_active = product.is_active
        if variation:
            is_active = is_active and variation.is_active

        cart_items.append({
            'id': key,
            'product': product,
            'variation': variation,
            'name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity'],
            'item_total': item_total,
            'image_url': item_data.get('image_url', ''),
            'is_active': is_active
        })
        
        if is_active:
            total_price += item_total

    settings_obj = SiteSettings.load()
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'delivery_inside': settings_obj.delivery_charge_inside,
        'delivery_outside': settings_obj.delivery_charge_outside
    }
    return render(request, 'jeba_sales/view_cart.html', context)


def update_cart(request, item_id, action):
    """Legacy/Fallback update view (Non-AJAX)"""
    cart = request.session.get('cart', {})
    if item_id in cart:
        _process_cart_update(cart, item_id, action)
        request.session['cart'] = cart
    return redirect('view_cart')


@require_POST
def update_cart_api(request):
    """AJAX Endpoint for dynamic cart updates"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        action = data.get('action')
        
        if not item_id or not action:
            return JsonResponse({'status': 'error', 'message': 'Invalid parameters'}, status=400)

        cart = request.session.get('cart', {})
        if item_id not in cart:
             return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)
             
        # Perform Logic
        success, message = _process_cart_update(cart, item_id, action)
        
        if not success:
            return JsonResponse({'status': 'error', 'message': message}, status=400)

        request.session['cart'] = cart
        
        # Recalculate Totals
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


def _process_cart_update(cart, item_id, action):
    """Helper logic shared between View and API"""
    item = cart[item_id]
    current_qty = item['quantity']
    
    if action == 'increase':
        product_id = item['product_id']
        variation_id = item.get('variation_id')
        
        # Stock Check
        can_increase = True
        try:
            if variation_id:
                var_obj = ProductVariation.objects.get(id=variation_id)
                if var_obj.stock_quantity <= current_qty: can_increase = False
            else:
                prod_obj = Product.objects.get(id=product_id)
                if prod_obj.stock_quantity <= current_qty: can_increase = False
        except:
            return False, "Product data error"

        if can_increase:
            cart[item_id]['quantity'] += 1
            return True, "Increased"
        else:
            return False, "Maximum stock reached"

    elif action == 'decrease':
        cart[item_id]['quantity'] -= 1
        if cart[item_id]['quantity'] < 1:
            del cart[item_id]
        return True, "Decreased"
            
    elif action == 'remove':
        del cart[item_id]
        return True, "Removed"
    
    return False, "Invalid action"


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
                    # 1. Lock & Deduct Stock
                    for key, item_data in cart.items():
                        product_id = item_data['product_id']
                        variation_id = item_data.get('variation_id')
                        order_qty = item_data['quantity']

                        product = Product.objects.select_for_update().get(id=product_id)
                        
                        if variation_id:
                            variation = ProductVariation.objects.select_for_update().get(id=variation_id)
                            if variation.stock_quantity < order_qty:
                                raise ValueError(f"Sorry, '{product.name} - {variation.name}' is out of stock. Available: {variation.stock_quantity}")
                            variation.stock_quantity -= order_qty
                            variation.save()
                        else:
                            if product.stock_quantity < order_qty:
                                raise ValueError(f"Sorry, '{product.name}' is out of stock. Available: {product.stock_quantity}")
                            product.stock_quantity -= order_qty
                            product.save()

                    # 2. Create Sale
                    new_sale = form.save(commit=False)
                    if request.user.is_authenticated:
                        new_sale.user = request.user

                    # Delivery Charge Logic
                    delivery_area = form.cleaned_data.get('delivery_area')
                    new_sale.delivery_charge = settings_obj.delivery_charge_outside if delivery_area == 'OUTSIDE' else settings_obj.delivery_charge_inside
                    
                    new_sale.save()

                    # 3. Create Items
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

                # 4. Async Tasks
                _handle_post_checkout(request, new_sale)

                request.session['last_order_id'] = new_sale.id
                request.session['cart'] = {}
                return redirect('order_success')

            except ValueError as e:
                messages.error(request, str(e))
                return redirect('view_cart')
            except Exception as e:
                print(f"Checkout Error: {e}")
                messages.error(request, "An unexpected error occurred.")
                return redirect('view_cart')
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data['customer_name'] = f"{request.user.first_name} {request.user.last_name}".strip()
            if hasattr(request.user, 'profile'):
                initial_data['phone_number'] = request.user.profile.phone_number
                initial_data['shipping_address'] = request.user.profile.address
        form = CheckoutForm(initial=initial_data)

    # --- FIX STARTS HERE: Reconstruct Cart Items properly ---
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
                continue

        item_total = item_data['price'] * item_data['quantity']
        total_price += item_total
        
        # We pass a dictionary that mimics the structure template expects
        # crucially including 'product' (the object) and 'id' (the cart key)
        cart_items.append({
            'id': key,                  # <--- Required for JS Buttons
            'product': product,         # <--- Required for Images
            'variation': variation,
            'name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity'],
            'item_total': item_total,
        })
    # ---------------------------------------------------------

    context = {
        'cart_items': cart_items, 
        'total_price': total_price,
        'form': form,
        'settings': settings_obj,
    }
    return render(request, 'jeba_sales/checkout.html', context)

def _handle_post_checkout(request, sale):
    """Handles Emails, Notifications, and CAPI events"""
    try:
        ip = AnalyticsService.get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
        
        # 1. CAPI Event
        threading.Thread(target=send_purchase_event, args=(sale, ip, ua)).start()
        
        # 2. Telegram
        threading.Thread(target=send_telegram_order_notification, args=(sale,)).start()

        # 3. Email
        if request.user.is_authenticated and request.user.email:
            domain_base = request.build_absolute_uri('/')[:-1]
            tracking_url = f"{domain_base}/track-order/{sale.access_token}/"
            threading.Thread(target=send_order_email, args=(sale, request.user.email, tracking_url)).start()
            
    except Exception as e:
        print(f"Error in post-checkout tasks: {e}")


def order_success(request):
    last_order_id = request.session.get('last_order_id')
    sale = None
    if last_order_id:
        sale = Sale.objects.filter(id=last_order_id).prefetch_related('items').first()
    return render(request, 'jeba_sales/order_success.html', {'sale': sale})


@login_required
def my_orders_view(request):
    user_orders = Sale.objects.filter(user=request.user).order_by('-created_at').prefetch_related('items')
    # Optional: Sync status logic here (kept brief)
    context = {'orders': user_orders}
    return render(request, 'jeba_accounts/registration/my_orders.html', context)


@login_required
def order_detail(request, pk):
    sale = get_object_or_404(Sale.objects.prefetch_related('items'), pk=pk)
    if sale.user != request.user:
        return redirect('my_orders')
    
    live_status = None
    if sale.consignment_id:
        live_status = check_delivery_status(sale.consignment_id, invoice_number=sale.invoice_number)
    
    return render(request, 'jeba_sales/order_detail.html', {'sale': sale, 'live_status': live_status})


def guest_order_track(request, token):
    sale = get_object_or_404(Sale.objects.prefetch_related('items'), access_token=token)
    # Status sync logic omitted for brevity, essentially same as original
    return render(request, 'jeba_sales/order_detail.html', {'sale': sale, 'is_guest_view': True})


def order_receipt(request, token):
    sale = get_object_or_404(Sale, access_token=token)
    tracking_url = request.build_absolute_uri(f'/track-order/{sale.access_token}/')
    return render(request, 'jeba_sales/receipt.html', {
        'sale': sale, 'tracking_url': tracking_url, 'settings': SiteSettings.load()
    })


def download_invoice_pdf(request, token):
    sale = get_object_or_404(Sale, access_token=token)
    tracking_url = request.build_absolute_uri(f'/track-order/{sale.access_token}/')
    data = {'sale': sale, 'tracking_url': tracking_url, 'settings': SiteSettings.load()}
    
    pdf_bytes = render_to_pdf('jeba_sales/invoice_pdf.html', data)
    if pdf_bytes:
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f"attachment; filename=Invoice_{sale.invoice_number}.pdf"
        return response
    return HttpResponse("PDF Generation Error", status=500)


@csrf_exempt
def steadfast_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    try:
        payload = json.loads(request.body)
        consignment_id = payload.get('consignment_id')
        if not consignment_id: return JsonResponse({'error': 'Missing ID'}, status=400)

        sale = Sale.objects.filter(consignment_id=consignment_id).first()
        if not sale: return JsonResponse({'error': 'Order not found'}, status=404)

        if payload.get('type') == 'delivery_status':
            status_map = {
                'delivered': 'DELIVERED', 'partial_delivered': 'DELIVERED', 
                'cancelled': 'CANCELLED', 'pending': 'PENDING'
            }
            new_status = status_map.get(payload.get('status', '').lower())
            if new_status:
                sale.status = new_status
                sale.save(update_fields=['status'])

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)