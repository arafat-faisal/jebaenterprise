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
from .models import Coupon

# --- CART VIEWS ---

@require_POST
def apply_coupon_api(request):
    """API to validate coupon"""
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip().upper()
        
        try:
            coupon = Coupon.objects.get(code=code, active=True)
        except Coupon.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid or expired coupon code.'})

        cart = request.session.get('cart', {})
        cart_total = sum(item['price'] * item['quantity'] for item in cart.values())
        
        if cart_total < coupon.min_spend:
            return JsonResponse({'status': 'error', 'message': f"Minimum spend of ৳{coupon.min_spend} required."})

        request.session['coupon_code'] = coupon.code
        request.session['discount_amount'] = float(coupon.discount_amount)
        
        return JsonResponse({
            'status': 'success',
            'discount': float(coupon.discount_amount),
            'message': f'Coupon {code} applied!'
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
def add_to_cart(request: HttpRequest, product_id):
    """
    Handles adding products.
    'Buy Now' logic: Resets cart to ensure single-item checkout.
    """
    variation_id = request.POST.get('variation_id')
    if variation_id and variation_id.strip():
        return add_to_cart_variation(request, variation_id)

    product = get_object_or_404(Product, id=product_id)
    
    if not product.is_active:
        messages.error(request, "This product is currently unavailable.")
        return redirect('product_detail', pk=product_id)
        
    if product.call_for_price:
        messages.info(request, "Please contact us for pricing.")
        return redirect('product_detail', pk=product_id)

    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1: quantity = 1
    except ValueError:
        quantity = 1

    if product.stock_quantity < quantity:
        messages.warning(request, f"Sorry, only {product.stock_quantity} units available in stock.")
        return redirect('product_detail', pk=product_id)

    # --- LOGIC START ---
    cart = request.session.get('cart', {})
    cart_item_id = str(product_id)
    action = request.POST.get('action') or request.GET.get('action')

    # FIX: If Buy Now, start with a fresh cart to ensure exclusive checkout
    if action == 'buy_now':
        cart = {} 

    if cart_item_id in cart:
        # If item exists (and we just cleared cart, this block won't hit for buy_now, which is correct)
        # But if it's 'add_to_cart', we increment
        if action == 'buy_now':
            cart[cart_item_id]['quantity'] = quantity
        else:
            new_total = cart[cart_item_id]['quantity'] + quantity
            if new_total > product.stock_quantity:
                messages.warning(request, f"You already have {cart[cart_item_id]['quantity']} in cart. Cannot add more.")
                return redirect('product_detail', pk=product_id)
            cart[cart_item_id]['quantity'] += quantity
    else:
        # Create new entry
        cart[cart_item_id] = {
            'product_id': product.id,
            'name': product.name,
            'price': float(product.selling_price),
            'quantity': quantity,
            'variation_id': None,
            'image_url': product.thumbnail.url if product.thumbnail else ''
        }

    request.session['cart'] = cart
    _trigger_atc_event(request, product)

    if action == 'buy_now':
        return redirect('checkout')
    
    messages.success(request, f"Added {product.name} to cart.")
    return redirect('product_detail', pk=product_id)


def add_to_cart_variation(request: HttpRequest, variation_id):
    """
    Handles adding variations.
    'Buy Now' logic: Resets cart to ensure single-item checkout.
    """
    variation = get_object_or_404(ProductVariation, id=variation_id)
    product = variation.product

    if not variation.is_active or not product.is_active:
        messages.error(request, "This variation is currently unavailable.")
        return redirect('product_detail', pk=product.id)

    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1: quantity = 1
    except ValueError:
        quantity = 1

    if variation.stock_quantity < quantity:
        messages.warning(request, f"Sorry, only {variation.stock_quantity} units of '{variation.name}' available.")
        return redirect('product_detail', pk=product.id)

    # --- LOGIC START ---
    cart = request.session.get('cart', {})
    cart_item_id = f"var_{variation_id}"
    action = request.POST.get('action') or request.GET.get('action')
    price_to_use = float(variation.selling_price)

    # FIX: If Buy Now, start with a fresh cart
    if action == 'buy_now':
        cart = {} 

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
    _trigger_atc_event(request, product)

    if action == 'buy_now':
        return redirect('checkout')
    
    messages.success(request, f"Added {variation.name} to cart.")
    return redirect('product_detail', pk=product.id)


def _trigger_atc_event(request, product):
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
    cart = request.session.get('cart', {})
    if item_id in cart:
        _process_cart_update(cart, item_id, action)
        request.session['cart'] = cart
    return redirect('view_cart')


@require_POST
def update_cart_api(request):
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        action = data.get('action')
        new_var_id = data.get('new_variation_id') 
        
        if not item_id or not action:
            return JsonResponse({'status': 'error', 'message': 'Invalid parameters'}, status=400)

        cart = request.session.get('cart', {})
        success, message = _process_cart_update(cart, item_id, action, new_var_id)
        
        if not success:
            return JsonResponse({'status': 'error', 'message': message}, status=400)

        request.session['cart'] = cart
        
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

        discount = request.session.get('discount_amount', 0)
        coupon_code = request.session.get('coupon_code')
        
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, active=True)
                if new_cart_total < coupon.min_spend:
                    discount = 0 
                    request.session['discount_amount'] = 0
                    message = "Coupon removed (below min spend)"
            except Coupon.DoesNotExist:
                discount = 0

        final_total = max(0, new_cart_total - discount)

        return JsonResponse({
            'status': 'success',
            'cart_total': new_cart_total,
            'discount': discount,
            'final_total': final_total,
            'item_total': new_item_total,
            'item_qty': new_item_qty,
            'cart_count': cart_count,
            'action_performed': action,
            'message': message
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    

def _process_cart_update(cart, item_id, action, new_var_id=None):
    if item_id not in cart:
        return False, "Item not found"

    item = cart[item_id]
    current_qty = item['quantity']
    
    if action == 'increase':
        product_id = item['product_id']
        variation_id = item.get('variation_id')
        
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

    elif action == 'swap':
        if not new_var_id: return False, "Missing Variation ID"
        
        try:
            new_var = ProductVariation.objects.get(id=new_var_id)
            if not new_var.is_active: return False, "Variation unavailable"
            
            if new_var.stock_quantity < current_qty:
                return False, f"Only {new_var.stock_quantity} left in {new_var.name}"

            new_key = f"var_{new_var_id}"
            
            if new_key in cart:
                cart[new_key]['quantity'] += current_qty
                if cart[new_key]['quantity'] > new_var.stock_quantity:
                    cart[new_key]['quantity'] -= current_qty
                    return False, "Not enough stock to merge"
            else:
                cart[new_key] = {
                    'product_id': item['product_id'],
                    'name': f"{new_var.product.name} ({new_var.name})",
                    'price': float(new_var.selling_price),
                    'quantity': current_qty,
                    'variation_id': new_var.id,
                    'image_url': item.get('image_url', '')
                }
            
            del cart[item_id]
            return True, "Variation Updated"

        except ProductVariation.DoesNotExist:
            return False, "Variation invalid"
    
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
                    for key, item_data in cart.items():
                        product_id = item_data['product_id']
                        variation_id = item_data.get('variation_id')
                        order_qty = item_data['quantity']

                        product = Product.objects.select_for_update().get(id=product_id)
                        
                        if variation_id:
                            variation = ProductVariation.objects.select_for_update().get(id=variation_id)
                            if variation.stock_quantity < order_qty:
                                raise ValueError(f"Sorry, '{product.name} - {variation.name}' is out of stock.")
                            variation.stock_quantity -= order_qty
                            variation.save()
                        else:
                            if product.stock_quantity < order_qty:
                                raise ValueError(f"Sorry, '{product.name}' is out of stock.")
                            product.stock_quantity -= order_qty
                            product.save()

                    new_sale = form.save(commit=False)
                    new_sale.user = request.user if request.user.is_authenticated else None

                    coupon_code = request.session.get('coupon_code')
                    discount = request.session.get('discount_amount', 0)
                    if coupon_code and discount > 0:
                        new_sale.coupon_code = coupon_code
                        new_sale.discount_amount = discount

                    delivery_area = form.cleaned_data.get('delivery_area')
                    new_sale.delivery_charge = settings_obj.delivery_charge_outside if delivery_area == 'OUTSIDE' else settings_obj.delivery_charge_inside
                    
                    new_sale.save()

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

                _handle_post_checkout(request, new_sale)
                
                request.session.pop('coupon_code', None)
                request.session.pop('discount_amount', None)
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

    cart_items = []
    cart_subtotal = 0
    
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
        cart_subtotal += item_total
        
        available_variations = None
        if product.variations.exists():
            available_variations = product.variations.filter(is_active=True)

        cart_items.append({
            'id': key,
            'product': product,
            'variation': variation,
            'variations': available_variations,
            'name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity'],
            'item_total': item_total,
        })

    discount = request.session.get('discount_amount', 0)
    final_total = max(0, cart_subtotal - discount)

    context = {
        'cart_items': cart_items, 
        'subtotal': cart_subtotal,
        'discount': discount,
        'total_price': final_total,
        'form': form,
        'settings': settings_obj,
    }
    return render(request, 'jeba_sales/checkout.html', context)

def _handle_post_checkout(request, sale):
    try:
        ip = AnalyticsService.get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
        threading.Thread(target=send_purchase_event, args=(sale, ip, ua)).start()
        threading.Thread(target=send_telegram_order_notification, args=(sale,)).start()

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