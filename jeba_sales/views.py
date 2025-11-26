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
# --- NEW IMPORT ---
from jeba_analytics.analytics_service import AnalyticsService
# -----------------------

from products.forms import CheckoutForm
from products.utils import send_order_email, render_to_pdf
from products.steadfast import check_delivery_status
from products.marketing import send_purchase_event


# --- CART VIEWS ---

def add_to_cart(request: HttpRequest, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # SAFETY: Prevent adding "Call for Price" items
    if product.call_for_price or product.selling_price <= 0:
        messages.error(request, "Please contact us directly for this product.")
        return redirect('product_detail', pk=product_id)

    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    action = request.POST.get('action')
    cart_item_id = str(product_id)

    if cart_item_id in cart:
        cart[cart_item_id]['quantity'] += quantity
    else:
        cart[cart_item_id] = {
            'name': product.name,
            'price': float(product.selling_price),
            'quantity': quantity,
            'product_id': product.id,
            'variation_id': None
        }

    request.session['cart'] = cart
    
    # TRACK CART EVENT WITH CONTEXT
    if not request.session.session_key: request.session.save()
    ProductEvent.objects.create(
        product=product,
        user=request.user if request.user.is_authenticated else None,
        session_id=request.session.session_key,
        event_type='CART',
        metadata=AnalyticsService.get_context(request) # <--- NEW
    )

    if action == 'buy_now':
        return redirect('checkout')
    return redirect('product_detail', pk=product_id)


def add_to_cart_variation(request: HttpRequest, variation_id):
    variation = get_object_or_404(ProductVariation, id=variation_id)
    product = variation.product
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    action = request.POST.get('action')

    cart_item_id = f"var_{variation_id}"

    if cart_item_id in cart:
        cart[cart_item_id]['quantity'] += quantity
    else:
        cart[cart_item_id] = {
            'name': f"{product.name} ({variation.name})",
            'price': float(variation.selling_price),
            'quantity': quantity,
            'product_id': product.id,
            'variation_id': variation.id
        }

    request.session['cart'] = cart
    
    if not request.session.session_key:
        request.session.save()
        
    # TRACK VARIATION CART EVENT
    ProductEvent.objects.create(
        product=product,
        user=request.user if request.user.is_authenticated else None,
        session_id=request.session.session_key,
        event_type='CART',
        metadata=AnalyticsService.get_context(request) # <--- NEW
    )

    if action == 'buy_now':
        return redirect('checkout')
    return redirect('product_detail', pk=product.id)


def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0

    for key, item_data in cart.items():
        try:
            product = Product.objects.get(id=item_data['product_id'])
            is_call_for_price = product.call_for_price or product.selling_price <= 0
        except Product.DoesNotExist:
            continue

        item_total = item_data['price'] * item_data['quantity']
        
        # --- FIX: Check for variation to be safe ---
        variation = None
        if item_data.get('variation_id'):
            try:
                variation = ProductVariation.objects.get(id=item_data['variation_id'])
            except ProductVariation.DoesNotExist:
                pass

        cart_items.append({
            'id': key,
            'product': product,   # <--- Added Object for Template access
            'variation': variation, # <--- Added Object
            'name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity'],
            'item_total': item_total,
            'call_for_price': is_call_for_price,
        })
        
        if not is_call_for_price:
            total_price += item_total

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'products/view_cart.html', context)


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
                variation = get_object_or_404(ProductVariation, id=variation_id)
                if variation.stock_quantity <= current_qty:
                    stock_ok = False
                    messages.error(request, f"Sorry, only {variation.stock_quantity} available for {variation.name}.")
            else:
                if product.stock_quantity <= current_qty:
                    stock_ok = False
                    messages.error(request, f"Sorry, only {product.stock_quantity} available.")
            
            if stock_ok:
                cart[item_id]['quantity'] += 1
                
        elif action == 'decrease':
            cart[item_id]['quantity'] -= 1
            if cart[item_id]['quantity'] < 1:
                del cart[item_id]
                
        elif action == 'remove':
            del cart[item_id]
    
    request.session['cart'] = cart
    return redirect('view_cart')


# --- CHECKOUT & ORDER VIEWS ---

def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
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
                        if item_data['variation_id']:
                            variation = ProductVariation.objects.get(id=item_data['variation_id'])
                        
                        SaleItem.objects.create(
                            sale=new_sale,
                            product=product,
                            variation=variation,
                            quantity=item_data['quantity'],
                            sold_price=item_data['price'],
                            buying_cost=product.buying_cost 
                        )
                        
                        # TRACK PURCHASE EVENT
                        ProductEvent.objects.create(
                            product=product,
                            user=request.user if request.user.is_authenticated else None,
                            session_id=request.session.session_key,
                            event_type='PURCHASE',
                            metadata=AnalyticsService.get_context(request) # <--- NEW
                        )
                
                threading.Thread(target=send_purchase_event, args=(new_sale, request)).start()
                
                request.session['last_order_id'] = new_sale.id

                if request.user.is_authenticated and request.user.email:
                    current_domain = request.get_host() 
                    email_thread = threading.Thread(
                        target=send_order_email, 
                        args=(new_sale, request.user.email, current_domain)
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

    # --- SMARTCODER FIX: Populate Cart Items with Real Product Objects ---
    cart_items = []
    total_price = 0
    for key, item_data in cart.items():
        try:
            product = Product.objects.get(id=item_data['product_id'])
        except Product.DoesNotExist:
            continue # Skip invalid products
            
        variation = None
        if item_data.get('variation_id'):
            try:
                variation = ProductVariation.objects.get(id=item_data['variation_id'])
            except ProductVariation.DoesNotExist:
                pass

        item_total = item_data['price'] * item_data['quantity']
        
        cart_items.append({
            'product': product,       # <--- CRITICAL FIX: Passing the object
            'variation': variation,   # <--- CRITICAL FIX: Passing the object
            'product_id': item_data['product_id'],
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
    return render(request, 'products/checkout.html', context)

def order_success(request):
    last_order_id = request.session.get('last_order_id')
    sale = None
    if last_order_id:
        sale = Sale.objects.filter(id=last_order_id).first()
        
    return render(request, 'products/order_success.html', {'sale': sale})

@login_required
def my_orders_view(request):
    user_orders = Sale.objects.filter(user=request.user).order_by('-created_at')

    for order in user_orders:
        if order.consignment_id and order.status not in ['DELIVERED', 'CANCELLED']:
            try:
                api_status = check_delivery_status(order.consignment_id)
                if api_status:
                    order.live_status_display = api_status
                    if api_status == 'delivered':
                        order.status = 'DELIVERED'
                        order.save(update_fields=['status'])
                    elif api_status == 'cancelled':
                        order.status = 'CANCELLED'
                        order.save(update_fields=['status'])
            except Exception as e:
                print(f"Error syncing order {order.id}: {e}")

    context = {
        'orders': user_orders
    }
    return render(request, 'registration/my_orders.html', context)

@login_required
def order_detail(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    
    if sale.user != request.user:
        return redirect('my_orders')

    live_status = None
    if sale.consignment_id:
        live_status = check_delivery_status(sale.consignment_id)
    
    context = {
        'sale': sale,
        'live_status': live_status 
    }
    return render(request, 'products/order_detail.html', context)

def guest_order_track(request, token):
    sale = get_object_or_404(Sale, access_token=token)
    
    live_status = None
    if sale.consignment_id:
        try:
            live_status = check_delivery_status(sale.consignment_id)
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
        'is_guest_view': True
    }
    return render(request, 'products/order_detail.html', context)

def order_receipt(request, token):
    sale = get_object_or_404(Sale, access_token=token)
    domain = request.build_absolute_uri('/')[:-1]
    tracking_url = f"{domain}/track-order/{sale.access_token}/"
    
    context = {
        'sale': sale,
        'tracking_url': tracking_url,
        'settings': SiteSettings.load()
    }
    return render(request, 'products/receipt.html', context)

def download_invoice_pdf(request, token):
    sale = get_object_or_404(Sale, access_token=token)
    domain = request.build_absolute_uri('/')[:-1]
    tracking_url = f"{domain}/track-order/{sale.access_token}/"
    
    data = {
        'sale': sale,
        'tracking_url': tracking_url,
        'settings': SiteSettings.load(),
    }
    
    pdf_bytes = render_to_pdf('products/invoice_pdf.html', data)
    
    if pdf_bytes:
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Invoice_{sale.invoice_number}.pdf"
        response['Content-Disposition'] = f"attachment; filename={filename}"
        return response
    
    return HttpResponse("Not found", status=404)