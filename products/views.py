from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, ProductVariation, Sale, SaleItem, ProductImage, CompetitorPrice, Category, SiteSettings, ProductEvent, SearchEvent, ScraperPreset
from django.http import HttpRequest, JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
import logging
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Avg, Case, When, Value, IntegerField
from .forms import CheckoutForm, ReviewForm, UserForm, ProfileForm, SignUpForm
from django.contrib.auth import logout
from django.core.mail import send_mail
from .models import Review, Wishlist, UserProfile

# --- UPDATED IMPORTS FROM UTILS ---
# We import the NEW send_welcome_email function here
from .utils import send_order_email, fetch_competitor_data, send_welcome_email
# ----------------------------------

from django.db import transaction
import threading
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .steadfast import check_delivery_status
from .marketing import send_purchase_event

# Get a logger for this file
logger = logging.getLogger(__name__)

# --- HELPER: Get Recommendations based on User History ---
def get_recommendations(request, limit=8):
    user = request.user if request.user.is_authenticated else None
    session_id = request.session.session_key
    
    if not user and not session_id:
        return Product.objects.none()

    # Get recent category interests
    recent_events = ProductEvent.objects.filter(event_type='VIEW')
    if user:
        recent_events = recent_events.filter(user=user)
    else:
        recent_events = recent_events.filter(session_id=session_id)
    
    # --- Ensure we have enough data ---
    if recent_events.count() < 3:
        return Product.objects.none()

    recent_category_ids = recent_events.order_by('-created_at')[:20].values_list('product__category_id', flat=True)

    if not recent_category_ids:
        return Product.objects.none()

    # Recommend products from those categories (excluding ones already seen)
    viewed_ids = recent_events.values_list('product_id', flat=True)
    recommendations = Product.objects.filter(category__id__in=recent_category_ids).exclude(id__in=viewed_ids).order_by('?')[:limit]
    return recommendations

# --- UPDATED: Homepage ---
def pricing_sheet(request):
    featured_product = Product.objects.filter(is_featured=True).order_by('-created_at').first()
    if not featured_product:
        featured_product = Product.objects.order_by('-created_at').first()

    new_arrivals = Product.objects.order_by('-created_at')[:4]
    
    best_sellers = Product.objects.annotate(total_sold=Sum('saleitem__quantity')).order_by('-total_sold')[:4]

    # Get Personalized Recommendations
    recommendations = get_recommendations(request, limit=4)

    # Discovery Feed (Random mix)
    all_products = Product.objects.all().order_by('?')[:30]

    context = {
        'featured_product': featured_product,
        'new_arrivals': new_arrivals,
        'best_sellers': best_sellers,
        'recommendations': recommendations,
        'products': all_products,
    }
    return render(request, "products/pricing_sheet.html", context)


# --- NEW: Dedicated Catalog View with Smart Sorting ---
def product_catalog(request):
    products = Product.objects.all().prefetch_related('images')
    
    # Filtering Logic
    category_id = request.GET.get('category')
    sort_by = request.GET.get('sort')

    if category_id:
        products = products.filter(category_id=category_id)
    
    # Annotate to put Call for Price items last (Value 1)
    products = products.annotate(
        sort_priority=Case(
            When(Q(call_for_price=True) | Q(selling_price__lte=0), then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    )

    if sort_by == 'new':
        products = products.order_by('sort_priority', '-created_at')
    elif sort_by == 'price-low':
        products = products.order_by('sort_priority', 'selling_price')
    elif sort_by == 'price-high':
        products = products.order_by('sort_priority', '-selling_price')
    else:
        # Default
        products = products.order_by('sort_priority', '-created_at')
        
    all_categories = Category.objects.all()

    # --- FETCH HERO PRODUCT ---
    hero_product = Product.objects.filter(is_featured=True).first()
    if not hero_product:
        hero_product = Product.objects.order_by('-created_at').first()

    context = {
        'products': products,
        'all_categories': all_categories,
        'active_category': category_id,
        'hero_product': hero_product,
    }
    return render(request, 'products/catalog.html', context)

# --- UPDATED: Product Detail (With Tracking) ---
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    # 1. TRACK VIEW EVENT
    if not request.session.session_key:
        request.session.save()
    ProductEvent.objects.create(
        product=product,
        user=request.user if request.user.is_authenticated else None,
        session_id=request.session.session_key,
        event_type='VIEW'
    )

    variations = product.variations.filter(is_active=True)
    
    # Related Products
    related_products = Product.objects.filter(category=product.category).exclude(id=pk)[:12]
    if not related_products:
        related_products = Product.objects.exclude(id=pk).order_by('-created_at')[:12]

    # Reviews & Wishlist
    reviews = product.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()
    
    # Recently Viewed
    session_id = request.session.session_key
    user = request.user if request.user.is_authenticated else None
    history_qs = ProductEvent.objects.filter(event_type='VIEW').exclude(product_id=pk)
    if user:
        history_qs = history_qs.filter(user=user)
    else:
        history_qs = history_qs.filter(session_id=session_id)
    
    # Get unique recent products
    recent_events = history_qs.order_by('-created_at').select_related('product')[:20]
    seen_ids = set()
    recently_viewed = []
    for event in recent_events:
        if event.product.id not in seen_ids:
            recently_viewed.append(event.product)
            seen_ids.add(event.product.id)
        if len(recently_viewed) >= 5: break

    context = {
        'product': product,
        'variations': variations,
        'related_products': related_products,
        'recently_viewed': recently_viewed,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'review_form': ReviewForm(),
        'in_wishlist': in_wishlist,
    }
    return render(request, "products/product_detail.html", context)


# --- UPDATED: Add to Cart (With Safety Check & Tracking) ---
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
    
    # TRACK CART EVENT
    if not request.session.session_key: request.session.save()
    ProductEvent.objects.create(
        product=product,
        user=request.user if request.user.is_authenticated else None,
        session_id=request.session.session_key,
        event_type='CART'
    )

    if action == 'buy_now':
        return redirect('checkout')
    return redirect('product_detail', pk=product_id)


# --- THIS IS THE NEW 'add_to_cart_variation' FUNCTION ---
def add_to_cart_variation(request: HttpRequest, variation_id):
    variation = get_object_or_404(ProductVariation, id=variation_id)
    product = variation.product # Get the parent product
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    action = request.POST.get('action')

    # We use a unique ID for the cart session
    cart_item_id = f"var_{variation_id}" # 'var_1'

    if cart_item_id in cart:
        cart[cart_item_id]['quantity'] += quantity
    else:
        cart[cart_item_id] = {
            'name': f"{product.name} ({variation.name})",
            'price': float(variation.selling_price),
            'quantity': quantity,
            'product_id': product.id,
            'variation_id': variation.id # Store the variation ID
        }

    request.session['cart'] = cart
    # --- NEW: TRACKING ---
    if not request.session.session_key:
        request.session.save()
        
    ProductEvent.objects.create(
        product=product, # ensure you get 'product' from variation.product
        user=request.user if request.user.is_authenticated else None,
        session_id=request.session.session_key,
        event_type='CART'
    )
    # ---------------------
    if action == 'buy_now':
        return redirect('checkout')
    return redirect('product_detail', pk=product.id)

# --- UPDATED: View Cart ---
def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0

    for key, item_data in cart.items():
        try:
            product = Product.objects.get(id=item_data['product_id'])
            # Check BOTH the checkbox AND if price is 0 or less
            is_call_for_price = product.call_for_price or product.selling_price <= 0
        except Product.DoesNotExist:
            continue # Skip deleted products

        item_total = item_data['price'] * item_data['quantity']
        
        cart_items.append({
            'id': key,
            'name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity'],
            'item_total': item_total,
            'call_for_price': is_call_for_price,
        })
        
        # Only add to total if it's NOT a call-for-price item
        if not is_call_for_price:
            total_price += item_total

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'products/view_cart.html', context)

def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('view_cart')
    settings = SiteSettings.load()
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                # A. ATOMIC TRANSACTION (Prevents Stock Crashes)
                with transaction.atomic():
                    # 1. Lock & Check Stock
                    for key, item_data in cart.items():
                        product_id = item_data['product_id']
                        variation_id = item_data.get('variation_id')
                        order_qty = item_data['quantity']

                        # Lock the row until we are done
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

                    # --- USE DYNAMIC CHARGES ---
                    delivery_area = form.cleaned_data.get('delivery_area')
                    if delivery_area == 'OUTSIDE':
                        new_sale.delivery_charge = settings.delivery_charge_outside
                    else:
                        new_sale.delivery_charge = settings.delivery_charge_inside
                    # ---------------------------
                    new_sale.save()

                    # 3. Create Items (Stock is deducted in SaleItem.save automatically)
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
                        # --- NEW: TRACKING PURCHASE ---
                        ProductEvent.objects.create(
                            product=product,
                            user=request.user if request.user.is_authenticated else None,
                            session_id=request.session.session_key,
                            event_type='PURCHASE'
                        )
                        # ------------------------------
                
                # --- NEW: 1. Send Server-Side Event (CAPI) ---
                threading.Thread(target=send_purchase_event, args=(new_sale, request)).start()
                
                # --- NEW: 2. Save ID for the Success Page ---
                request.session['last_order_id'] = new_sale.id

                # B. BACKGROUND EMAIL
                if request.user.is_authenticated and request.user.email:
                    email_thread = threading.Thread(target=send_order_email, args=(new_sale, request.user.email))
                    email_thread.start()

                # C. SUCCESS
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

    cart_items = []
    total_price = 0
    for key, item_data in cart.items():
        item_total = item_data['price'] * item_data['quantity']
        cart_items.append({
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
        'settings': settings,
    }
    return render(request, 'products/checkout.html', context)

def order_success(request):
    last_order_id = request.session.get('last_order_id')
    sale = None
    if last_order_id:
        sale = Sale.objects.filter(id=last_order_id).first()
        
    return render(request, 'products/order_success.html', {'sale': sale})

def print_products_page(request):
    product_ids_str = request.GET.get('ids', '')
    product_ids = [int(id) for id in product_ids_str.split(',') if id.isdigit()]
    
    products = Product.objects.filter(id__in=product_ids).prefetch_related('variations')

    all_cols = {
        'image': 'Image',
        'name': 'Product Name',
        'description': 'Description',
        'selling_price': 'Base Price',
        'variations': 'Price Variations',
        'competitor_prices': 'Competitor Prices',
        'box_quantity': 'Box Quantity',
        'stock': 'Stock',
    }
    
    selected_cols_keys = request.GET.getlist('cols')
    blank_cols_keys = request.GET.getlist('blank_cols')
    
    if not selected_cols_keys:
        selected_cols_keys = ['image', 'name', 'description', 'selling_price', 'box_quantity']
    
    col_headers = [all_cols[key] for key in selected_cols_keys if key in all_cols]
    cols_list = selected_cols_keys

    context = {
        'products': products,
        'col_headers': col_headers,
        'cols_list': cols_list,
        'blank_cols_keys': blank_cols_keys,
        'all_cols': all_cols,
    }
    return render(request, 'products/print_page.html', context)

# --- UPDATED ADMIN SCRAPER VIEW ---
@staff_member_required
def admin_scraper_view(request):
    # --- GET Request Logic ---
    if request.method == 'GET':
        all_products = Product.objects.all().order_by('name')
        presets = ScraperPreset.objects.all()
        context = {
            'all_products': all_products,
            'presets': presets
        }
        return render(request, 'products/admin_scraper.html', context)

    # --- POST Request Logic ---
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # FEATURE 1: MANUAL PRICE SAVE (Updated for Min/Max)
        if action == 'save_price':
            product_id = request.POST.get('product_id')
            price = request.POST.get('price')
            min_price = request.POST.get('min_price')
            max_price = request.POST.get('max_price')
            
            if not product_id:
                return JsonResponse({'success': False, 'error': 'Missing Product ID'})
            
            try:
                defaults = {}
                if min_price and max_price:
                    defaults['min_price'] = float(min_price)
                    defaults['max_price'] = float(max_price)
                elif price:
                    defaults['min_price'] = float(price)
                    defaults['max_price'] = float(price)
                else:
                     return JsonResponse({'success': False, 'error': 'Missing Price Data'})

                product = Product.objects.get(id=product_id)
                CompetitorPrice.objects.update_or_create(
                    product=product,
                    website_name="Daraz", 
                    defaults=defaults
                )
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})

        # FEATURE 3: SAVE PRESET
        if action == 'save_preset':
            try:
                name = request.POST.get('name')
                ScraperPreset.objects.create(
                    name=name,
                    image_weight=request.POST.get('image_weight'),
                    text_weight=request.POST.get('text_weight'),
                    confidence_threshold=request.POST.get('confidence_threshold'),
                    text_slam_dunk=request.POST.get('text_slam_dunk'),
                    image_slam_dunk=request.POST.get('image_slam_dunk')
                )
                return JsonResponse({'success': True})
            except Exception as e: return JsonResponse({'success': False, 'error': str(e)})

        # FEATURE 4: DELETE PRESET
        if action == 'delete_preset':
            try:
                preset_id = request.POST.get('preset_id')
                ScraperPreset.objects.filter(id=preset_id).delete()
                return JsonResponse({'success': True})
            except Exception as e: return JsonResponse({'success': False, 'error': str(e)})

        # FEATURE 2: RUN SCRAPER
        product_id = request.POST.get('product_id', '')
        search_term = request.POST.get('search_term', '')
        manual_image = request.FILES.get('image')
        
        if not product_id:
            return JsonResponse({'error': 'Product ID missing.'}, status=400)
        
        product = get_object_or_404(Product, id=product_id)
        
        manual_bytes = None
        if manual_image:
            manual_bytes = manual_image.read()

        # Get Settings
        try:
            image_weight = float(request.POST.get('image_weight', 0.3))
            text_weight = float(request.POST.get('text_weight', 0.7))
            confidence_threshold = int(request.POST.get('confidence_threshold', 60))
            text_slam_dunk = int(request.POST.get('text_slam_dunk', 85))
            image_slam_dunk = int(request.POST.get('image_slam_dunk', 90))
        except ValueError:
            image_weight = 0.3
            text_weight = 0.7
            confidence_threshold = 60
            text_slam_dunk = 85
            image_slam_dunk = 90

        # Call helper. save_to_db=True to AUTO-SAVE results as requested
        result = fetch_competitor_data(
            product, 
            search_term, 
            manual_image_bytes=manual_bytes, 
            save_to_db=True,
            image_weight=image_weight,
            text_weight=text_weight,
            confidence_threshold=confidence_threshold,
            text_slam_dunk=text_slam_dunk,
            image_slam_dunk=image_slam_dunk
        )
        
        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse({'error': result.get('error', 'Unknown error')}, status=500)

def register_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            if user.email: 
                try:
                    # --- REPLACED PLAIN TEXT WITH HTML TEMPLATE ---
                    # We now call the function in utils.py that attaches the logo
                    # and sends the nice HTML welcome email.
                    threading.Thread(target=send_welcome_email, args=(user,)).start()
                    # -----------------------------------------------
                except:
                    pass 

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = SignUpForm()

    context = {'form': form}
    return render(request, 'registration/register.html', context)

@login_required
def my_orders_view(request):
    user_orders = Sale.objects.filter(user=request.user).order_by('-created_at')

    # --- SYNC STATUS WITH STEADFAST ---
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


def search_view(request):
    query = request.GET.get('q')
    image_file = request.FILES.get('image')
    
    products = Product.objects.all()
    
    if request.method == 'GET' and query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
        # Track Search
        if not request.session.session_key: request.session.save()
        SearchEvent.objects.create(
            query=query,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key
        )

    elif request.method == 'POST' and image_file:
        pass # Placeholder for Image Search

    category_id = request.GET.get('category')
    sort_by = request.GET.get('sort')

    if category_id:
        products = products.filter(category_id=category_id)

    if sort_by == 'new':
        products = products.order_by('-created_at')
    elif sort_by == 'price-low':
        products = products.order_by('selling_price')
    elif sort_by == 'price-high':
        products = products.order_by('-selling_price')

    all_categories = Category.objects.all()

    context = {
        'products': products,
        'query': query,
        'is_image_search': bool(image_file),
        'all_categories': all_categories,
        'active_category': category_id,
        'active_sort': sort_by
    }
    
    return render(request, 'products/search_results.html', context)

def user_logout(request):
    logout(request)
    return redirect('pricing_sheet')

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, 'Review submitted!')
    return redirect('product_detail', pk=product_id)

@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wish_item = Wishlist.objects.filter(user=request.user, product=product).first()
    
    if wish_item:
        wish_item.delete()
        messages.info(request, 'Removed from Wishlist')
    else:
        Wishlist.objects.create(user=request.user, product=product)
        messages.success(request, 'Added to Wishlist')
        
    return redirect(request.META.get('HTTP_REFERER', 'pricing_sheet'))

@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user)
    return render(request, 'products/wishlist.html', {'items': items})

@login_required
def profile_view(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=request.user.profile)
    
    return render(request, 'registration/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

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

@login_required
def user_dashboard(request):
    user = request.user
    
    if request.method == 'POST' and 'update_profile' in request.POST:
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, instance=user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_dashboard')
            
    elif request.method == 'POST' and 'change_password' in request.POST:
        password_form = PasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Please correct the error below.')
    
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=user.profile)
        password_form = PasswordChangeForm(user)

    recent_orders = Sale.objects.filter(user=user).order_by('-created_at')[:3]
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form,
        'recent_orders': recent_orders
    }
    return render(request, 'registration/dashboard.html', context)

# --- NEW: TRACK SHARE EVENT ---
def track_share(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=product_id)
        if not request.session.session_key:
            request.session.save()
            
        ProductEvent.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key,
            event_type='SHARE'
        )
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

# --- CUSTOM ERROR PAGES ---
def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)

def about_us(request):
    return render(request, 'products/about.html')

def contact_us(request):
    return render(request, 'products/contact.html')