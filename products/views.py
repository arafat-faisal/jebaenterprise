from django.shortcuts import render, get_object_or_404, redirect
from .models import Product,ProductVariation, Sale, SaleItem, ProductImage,  CompetitorPrice,Category , SiteSettings, ProductEvent, SearchEvent  # Import your Product model
from django.http import HttpRequest

# --- ADD ALL THESE IMPORTS AT THE TOP ---
import json
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

import requests
import imagehash
from PIL import Image
from io import BytesIO

from thefuzz import fuzz


import logging

from django.conf import settings

from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages

from django.contrib.auth.decorators import login_required

from django.db.models import Q

from .forms import CheckoutForm

from django.core.files.storage import default_storage

from django.contrib.auth import logout # Import this

from django.core.mail import send_mail
from django.db.models import Avg
from .forms import ReviewForm, UserForm, ProfileForm,SignUpForm # Import new forms
from .models import Review, Wishlist, UserProfile # Import new models

# Add these imports at the top
from django.db.models import Sum, Count

from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives

from .utils import send_order_email # Import the new helper

from django.db import transaction
import threading
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .steadfast import check_delivery_status # Import helper

from .marketing import send_purchase_event



# def pricing_sheet(request):
#         # 1. Start with all products (and prefetch related data)
#         all_products = Product.objects.prefetch_related('images', 'variations').all()
        
#         # 2. Get Search Query (q) and Category Filter
#         search_query = request.GET.get('q')
#         category_id = request.GET.get('category')

#         # 3. Apply Filters
#         if search_query:
#             # Filter products where name OR description contains the query
#             all_products = all_products.filter(
#                 Q(name__icontains=search_query) | Q(description__icontains=search_query)
#             )
            
#         if category_id:
#             all_products = all_products.filter(category_id=category_id)

#         # 4. Final Product Ordering
#         all_products = all_products.order_by('name')

#         # 5. Get all Categories for the filter bar
#         all_categories = Category.objects.all().order_by('name')

#         # 6. Pass data to the template
#         context = {
#             'products': all_products,
#             'all_categories': all_categories,
#             'active_category': category_id # Pass this to highlight the active filter
#         }
        
#         return render(request, "products/pricing_sheet.html", context)
# --- UPDATE: Homepage View ---
def pricing_sheet(request):
    # 1. Get the Hero Product (The one you checked in Admin)
    # We try to get the newest one marked 'is_featured'. 
    # If none are checked, we fallback to the newest product.
    featured_product = Product.objects.filter(is_featured=True).order_by('-created_at').first()
    if not featured_product:
        featured_product = Product.objects.order_by('-created_at').first()

    # 2. Get New Arrivals (Last 4 created)
    new_arrivals = Product.objects.order_by('-created_at')[:4]

    # 3. Get Best Sellers (Calculated by summing SaleItems)
    # This is "Real Data" logic!
    best_sellers = Product.objects.annotate(
        total_sold=Sum('saleitem__quantity')
    ).order_by('-total_sold')[:4]

    # 4. Get a mix for the bottom grid
    all_products = Product.objects.all().order_by('?')[:8] # Random mix for discovery

    context = {
        'featured_product': featured_product,
        'new_arrivals': new_arrivals,
        'best_sellers': best_sellers,
        'products': all_products,
    }
    return render(request, "products/pricing_sheet.html", context)

# --- NEW: Dedicated Catalog View ---
def product_catalog(request):
    products = Product.objects.all().prefetch_related('images')
    
    # Filtering Logic (Keep existing)
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

    # --- NEW: FETCH HERO PRODUCT ---
    # 1. Try to find a product marked as 'is_featured'
    hero_product = Product.objects.filter(is_featured=True).first()
    # 2. If none, fallback to the newest product
    if not hero_product:
        hero_product = Product.objects.order_by('-created_at').first()

    context = {
        'products': products,
        'all_categories': all_categories,
        'active_category': category_id,
        'hero_product': hero_product, # <--- Pass this to the template
    }
    return render(request, 'products/catalog.html', context)

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    # --- NEW: TRACKING ---
    # Ensure we have a session ID even for anonymous users
    if not request.session.session_key:
        request.session.save()
        
    ProductEvent.objects.create(
        product=product,
        user=request.user if request.user.is_authenticated else None,
        session_id=request.session.session_key,
        event_type='VIEW'
    )
    # ---------------------

    variations = product.variations.filter(is_active=True)
    
    # Related Products logic (Keep existing)
    related_products = Product.objects.filter(category=product.category).exclude(id=pk)[:4]
    if not related_products:
        related_products = Product.objects.exclude(id=pk).order_by('-created_at')[:4]

    # --- NEW: Reviews & Wishlist Data ---
    reviews = product.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()
    
    context = {
        'product': product,
        'variations': variations,
        'related_products': related_products,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'review_form': ReviewForm(),
        'in_wishlist': in_wishlist,
    }
    return render(request, "products/product_detail.html", context)


# --- THIS IS YOUR MODIFIED 'add_to_cart' FOR MAIN PRODUCTS ---
def add_to_cart(request: HttpRequest, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    action = request.POST.get('action')

    # We use a unique ID for the cart session
    cart_item_id = str(product_id) # 'product_1'

    if cart_item_id in cart:
        cart[cart_item_id]['quantity'] += quantity
    else:
        cart[cart_item_id] = {
            'name': product.name,
            'price': float(product.selling_price),
            'quantity': quantity,
            'product_id': product.id, # Store the product ID
            'variation_id': None # No variation
        }

    request.session['cart'] = cart

    # --- NEW: TRACKING ---
    if not request.session.session_key:
        request.session.save()

    ProductEvent.objects.create(
        product=product,
        user=request.user if request.user.is_authenticated else None,
        session_id=request.session.session_key,
        event_type='CART'
    )
    # ---------------------

    # <--- NEW LOGIC HERE ---
    if action == 'buy_now':
        return redirect('checkout')
    # -----------------------

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
    # Redirect back to the main product's page
    return redirect('product_detail', pk=product.id)

# --- ADD THIS NEW FUNCTION ---
def view_cart(request):
    # 1. Get the cart from the session
    cart = request.session.get('cart', {})

    # 2. We need to re-format the cart data for the template
    cart_items = []
    total_price = 0
    for product_id, item_data in cart.items():
        item_total = item_data['price'] * item_data['quantity']
        cart_items.append({
            'id': product_id,
            'name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity'],
            'item_total': item_total,
        })
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
                # We run this in a thread so it doesn't slow down checkout
                threading.Thread(target=send_purchase_event, args=(new_sale, request)).start()
                
                # --- NEW: 2. Save ID for the Success Page ---
                request.session['last_order_id'] = new_sale.id



                # B. BACKGROUND EMAIL (Makes Checkout Instant)
                if request.user.is_authenticated and request.user.email:
                    # Run email in a separate thread so user doesn't wait
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
            'product_id': item_data['product_id'],  # <--- ADD THIS LINE
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



# --- ADD THIS SIMPLE SUCCESS VIEW ---
def order_success(request):
    # Retrieve the order that was just made
    last_order_id = request.session.get('last_order_id')
    sale = None
    if last_order_id:
        sale = Sale.objects.filter(id=last_order_id).first()
        
    return render(request, 'products/order_success.html', {'sale': sale})

def print_products_page(request):
    # --- Part 1: Get Product IDs (no change) ---
    product_ids_str = request.GET.get('ids', '')
    product_ids = [int(id) for id in product_ids_str.split(',') if id.isdigit()]
    
    products = Product.objects.filter(id__in=product_ids).prefetch_related('variations')

    # --- Part 2: Get Column Preferences (UPDATED) ---
    
    # Define all possible columns and their friendly names
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
    
    # Get the list of checked boxes for VISIBILITY
    selected_cols_keys = request.GET.getlist('cols')
    
    # --- NEW: Get the list of checked boxes for BLANK DATA ---
    blank_cols_keys = request.GET.getlist('blank_cols')
    
    # If no columns were selected (e.g., first load), use a default
    if not selected_cols_keys:
        selected_cols_keys = ['image', 'name', 'description', 'selling_price', 'box_quantity']
    
    # Build the list of headers based on the selected keys
    col_headers = [all_cols[key] for key in selected_cols_keys if key in all_cols]
    
    # The list of keys is just the selected_cols_keys
    cols_list = selected_cols_keys

    # --- Part 3: Send to Template (UPDATED) ---
    context = {
        'products': products,
        'col_headers': col_headers,  # The list of names for the <th> row
        'cols_list': cols_list,      # The list of keys for the <td> rows
        'blank_cols_keys': blank_cols_keys, # NEW: List of columns to blank out
        'all_cols': all_cols,        # The full dictionary to build the checkboxes
    }
    return render(request, 'products/print_page.html', context)

# --- ADD THIS NEW VIEW AT THE BOTTOM ---
# ... (all your other imports) ...
# ... (all your other imports: requests, imagehash, PIL, BytesIO, etc.) ...

# --- ADD THIS LINE ---
# Get a logger for this file
logger = logging.getLogger(__name__)

# ... (all your imports) ...

@staff_member_required
def admin_scraper_view(request):
    # --- GET Request Logic: (No change) ---
    if request.method == 'GET':
        all_products = Product.objects.all().order_by('name')
        context = {
            'all_products': all_products
        }
        return render(request, 'products/admin_scraper.html', context)

    # --- POST Request Logic: Run the "Gallery AI" Scraper ---
    if request.method == 'POST':
        product_id = request.POST.get('product_id', '')
        search_term = request.POST.get('search_term', '')
        if not product_id or not search_term:
            return JsonResponse({'error': 'Product ID or search term missing.'}, status=400)
        
        # --- (AI thresholds - no change) ---
        IMAGE_WEIGHT = 0.2
        TEXT_WEIGHT = 0.8
        CONFIDENCE_THRESHOLD = 65
        TEXT_SLAM_DUNK = 85
        
        try:
            # --- 1. Get our local product's "fingerprints" (PLURAL) ---
            local_product = get_object_or_404(Product.objects.prefetch_related('images'), id=product_id)
            
            # --- THIS IS THE NEW GALLERY LOGIC ---
            local_images = local_product.images.all()
            if not local_images:
                return JsonResponse({'error': 'Your selected product has no images in its gallery.'}, status=400)

            # Generate a LIST of hashes, one for each image in our gallery
            local_hashes = []
            for img in local_images:
                try:
                    local_image_pil = Image.open(img.image.path)
                    local_hashes.append(imagehash.phash(local_image_pil))
                except Exception as e:
                    logger.warning(f"Could not load local image {img.id}: {e}")
            
            if not local_hashes:
                 return JsonResponse({'error': 'Could not read any of the images in your gallery.'}, status=400)
            
            local_name = local_product.name
            logger.info(f"--- Loaded {len(local_hashes)} local hashes for {local_name} ---")

            # --- 2. Run the Playwright scraper (No change) ---
            logger.info(f"--- Scraping for: {local_name} ---")
            logger.info(f"--- Matching against: {local_name} | Scraping for: {search_term} ---")
            with sync_playwright() as p:
                # ... (browser launch, goto, etc. is all the same) ...
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent='Mozilla/5.0 ...')
                
                
                search_url = f"https://www.daraz.com.bd/catalog/?q={search_term.replace(' ', '+')}"
                page.goto(search_url, timeout=20000)
                page.wait_for_selector('[data-qa-locator="product-item"]', timeout=15000)
                # --- THIS IS THE NEW SCROLLING LOGIC ---
                logger.info("--- Forcing lazy-load by scrolling... ---")
                for i in range(15):  # Scroll down 5 times to load everything
                    page.evaluate("window.scrollBy(0, window.innerHeight)")
                    page.wait_for_timeout(1000) # Wait 0.5 sec for images to load
                # --- END OF NEW LOGIC ---

                html_content = page.content()
                browser.close()
                
            # --- 3. Parse and Compare (The "Gallery AI" Match) ---
            soup = BeautifulSoup(html_content, 'html.parser')
            product_items = soup.find_all(attrs={'data-qa-locator': 'product-item'})
            logger.info(f"--- Found {len(product_items)} items. Running Gallery AI filter... ---")

            results = []
            for item in product_items:
                try:
                    # ... (finding name, price, image_url is all the same) ...
                    name_link_tag = item.find('div', class_='RfADt').find('a')
                    price_span = item.find('div', class_='aBrP0').find('span', class_='ooOxS')
                    image_tag = item.find('img')

                    # --- THIS IS THE NEW, FINAL IMAGE LOGIC ---
                    image_url = None
                    if image_tag:
                        # 1. Try to get 'data-src' first (Trick A)
                        if image_tag.get('data-src'):
                            image_url = image_tag['data-src']
                        # 2. If not, try to get 'srcset' (Trick B)
                        elif image_tag.get('srcset'):
                            # srcset looks like: "//url1.jpg 1x, //url2.jpg 2x"
                            # We'll grab the first URL from the list
                            first_url_part = image_tag['srcset'].split(',')[0]
                            image_url = first_url_part.split(' ')[0] # Get just "//url1.jpg"
                        # 3. If not, fall back to 'src'
                        else:
                            image_url = image_tag.get('src')
                    # --- END OF NEW LOGIC ---

                    if not all([name_link_tag, price_span, image_url]):
                        continue # Skip if key data is missing

                    # Make sure the URL is complete
                    if image_url.startswith('//'):
                        image_url = 'https:' + image_url

                    # We also need to check for 'data:' images one last time
                    if image_url.startswith('data:'):
                        # This is an item we can't parse yet. Log its HTML for inspection.
                        try:
                            # Use settings.BASE_DIR to find your root folder
                            with open(settings.BASE_DIR / 'scraper_errors.log', 'a', encoding='utf-8') as f:
                                f.write("---" * 20 + "\n")
                                f.write(f"SKIPPING ITEM - 'data:image' found. No 'data-src' or 'srcset'.\n")
                                f.write("HTML OF FAILED ITEM:\n")
                                f.write(item.prettify() + "\n")
                                f.write("---" * 20 + "\n\n")

                            # Log a *new* message to the terminal
                            logger.warning(f"--- Skipping item: Still a data:image. See scraper_errors.log for HTML. ---")

                        except Exception as e_write:
                            logger.error(f"--- FAILED TO WRITE TO scraper_errors.log: {e_write} ---")

                        continue # Skip this item
                    
                    scraped_name = name_link_tag.text.strip()
                    scraped_url = "https:" + name_link_tag['href']
                    scraped_price = price_span.text.replace('৳', '').replace(',', '').strip()
                    
                    # --- 5. Calculate Confidence Scores (UPDATED LOGIC) ---
                    
                    # A. Image Score (Many-to-One Comparison)
                    response = requests.get(image_url)
                    scraped_image = Image.open(BytesIO(response.content))
                    scraped_hash = imagehash.phash(scraped_image)
                    
                    # Compare the scraped hash to EVERY hash in our gallery
                    # and find the BEST (minimum) match
                    min_distance = 64 # Max possible distance
                    for local_hash in local_hashes:
                        distance = local_hash - scraped_hash
                        if distance < min_distance:
                            min_distance = distance
                    
                    # Now we have the best possible image score
                    image_score = (1 - min_distance / 64) * 100
                    
                    # B. Text Score (No change)
                    text_score = fuzz.ratio(local_name.lower(), scraped_name.lower())
                    
                    # C. Final Weighted Score (No change)
                    confidence_score = (image_score * IMAGE_WEIGHT) + (text_score * TEXT_WEIGHT)

                    # --- 6. The "Pinpoint" Filter (No change) ---
                    if (confidence_score >= CONFIDENCE_THRESHOLD) or (text_score >= TEXT_SLAM_DUNK):
                        logger.info(f"--- MATCH: '{scraped_name}' (Final: {confidence_score:.0f}%) | Text: {text_score:.0f}% | Image: {image_score:.0f}% [BestDist: {min_distance}]")
                        results.append({
                            'name': scraped_name,
                            'price': scraped_price,
                            'url': scraped_url,
                            'match_score': f"{confidence_score:.0f}"
                        })
                    else:
                        logger.info(f"--- NO MATCH: '{scraped_name}' (Final: {confidence_score:.0f}%) | Text: {text_score:.0f}% | Image: {image_score:.0f}% [BestDist: {min_distance}]")
                # ----
                except Exception as e:
                    # Log the detailed error to a dedicated file
                    try:
                        # Use settings.BASE_DIR to find your root folder
                        with open(settings.BASE_DIR / 'scraper_errors.log', 'a', encoding='utf-8') as f:
                            f.write("---" * 20 + "\n")
                            f.write(f"SKIPPING ITEM - PARSING ERROR: {e}\n")
                            f.write("HTML OF FAILED ITEM:\n")
                            f.write(item.prettify() + "\n") # Write the full, clean HTML
                            f.write("---" * 20 + "\n\n")

                        # Also log a short message to the main jebaenterprise.log
                        logger.warning(f"--- Skipping item due to parsing error: {e}. See scraper_errors.log for HTML. ---")

                    except Exception as e_write:
                        # If writing the log file fails, just log the original error
                        logger.error(f"--- FAILED TO WRITE TO scraper_errors.log: {e_write} ---")
                        logger.warning(f"--- Skipping item due to parsing error: {e}. Could not get HTML. ---")

                    continue # Continue to the next item

            results.sort(key=lambda x: float(x['match_score']), reverse=True)
            # --- ADD THIS NEW BLOCK TO SAVE DATA ---
            if results:
                # We found some matches, let's save the price range
                try:
                    # Get all prices as floats
                    prices = [float(r['price']) for r in results if r['price']]
                    if prices:
                        min_p = min(prices)
                        max_p = max(prices)

                        # Use update_or_create to add/update the price for this product
                        CompetitorPrice.objects.update_or_create(
                            product=local_product,
                            website_name="Daraz",
                            defaults={
                                'min_price': min_p,
                                'max_price': max_p
                            }
                        )
                        logger.info(f"--- Saved Daraz prices for {local_product.name}: min={min_p}, max={max_p} ---")

                except Exception as e_save:
                    logger.error(f"--- FAILED to save competitor prices: {e_save} ---")
            # --- END OF NEW BLOCK ---

            return JsonResponse({'success': True, 'products': results})
                
        except Exception as e:
            logger.error(f"--- SCRAPING FAILED (Outer Try): {e} ---")
            return JsonResponse({'error': f'Scraping failed: {str(e)}'}, status=500)
        

# --- ADD THIS NEW FUNCTION ---
def register_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # --- SEND WELCOME EMAIL (Only if email exists) ---
            if user.email: # <--- ADD THIS CHECK
                try:
                    send_mail(
                        subject=f"Welcome to Jeba Enterprise, {user.first_name}!",
                        message=f"Hi {user.first_name},\n\nThank you for creating an account with us. We are excited to have you!\n\nYou can now log in to view your order history and manage your profile.\n\nBest regards,\nThe Jeba Team",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
                except:
                    pass 
            # -------------------------------------------------

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = SignUpForm()

    context = {'form': form}
    return render(request, 'registration/register.html', context)


# --- ADD THIS NEW FUNCTION ---
# This decorator prevents anyone who isn't logged in from seeing the page
@login_required
def my_orders_view(request):
    # Get all orders
    user_orders = Sale.objects.filter(user=request.user).order_by('-created_at')

    # --- NEW: SYNC STATUS WITH STEADFAST ---
    for order in user_orders:
        # Only check if we have a consignment ID and the order isn't already closed
        if order.consignment_id and order.status not in ['DELIVERED', 'CANCELLED']:
            try:
                # Call API
                api_status = check_delivery_status(order.consignment_id)
                
                if api_status:
                    # 1. Attach live status to the object (for this request only)
                    # We use a temporary attribute 'live_status_display'
                    order.live_status_display = api_status
                    
                    # 2. Auto-Update Database if final status reached
                    if api_status == 'delivered':
                        order.status = 'DELIVERED'
                        order.save(update_fields=['status'])
                    elif api_status == 'cancelled':
                        order.status = 'CANCELLED'
                        order.save(update_fields=['status'])
                    elif api_status == 'partial_delivered':
                         # Optional: You might want a custom status for this, 
                         # or just keep it as SHIPPED but show the label.
                         pass
            except Exception as e:
                print(f"Error syncing order {order.id}: {e}")
    # ---------------------------------------

    context = {
        'orders': user_orders
    }
    return render(request, 'registration/my_orders.html', context)


@login_required
def order_detail(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    
    # Security Check
    if sale.user != request.user:
        return redirect('my_orders')

    # --- LIVE TRACKING LOGIC ---
    live_status = None
    if sale.consignment_id:
        # If sent to courier, get the REAL status from API
        live_status = check_delivery_status(sale.consignment_id)
    
    # Pass both local sale data and live status
    context = {
        'sale': sale,
        'live_status': live_status 
    }
    return render(request, 'products/order_detail.html', context)


def search_view(request):
    query = request.GET.get('q')
    image_file = request.FILES.get('image')
    
    # 1. Start with all products
    products = Product.objects.all()
    
    # --- SEARCH LOGIC ---
    if request.method == 'GET' and query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
    elif request.method == 'POST' and image_file:
        # ... (Keep your existing Image Search Logic here) ...
        # For brevity, I am not repeating the whole imagehash block, 
        # but KEEP IT EXACTLY AS IT WAS inside this elif.
        # ...
        pass # Placeholder: Put your imagehash code back here!

    # --- NEW: APPLY FILTERS (Category & Sort) ON SEARCH RESULTS ---
    # This allows users to filter/sort *within* their search results
    # --- NEW: TRACKING SEARCH ---
    if request.method == 'GET' and query:
        if not request.session.session_key:
            request.session.save()
            
        SearchEvent.objects.create(
            query=query,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key
        )
    # ----------------------------
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

    # Get categories for the sidebar
    all_categories = Category.objects.all()

    context = {
        'products': products,
        'query': query,
        'is_image_search': bool(image_file),
        'all_categories': all_categories, # Needed for sidebar
        'active_category': category_id,
        'active_sort': sort_by
    }
    
    return render(request, 'products/search_results.html', context)

def user_logout(request):
    logout(request)
    return redirect('pricing_sheet')


# --- FEATURE 1: ADD REVIEW ---
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

# --- FEATURE 2: WISHLIST LOGIC ---
@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # Check if already in wishlist
    wish_item = Wishlist.objects.filter(user=request.user, product=product).first()
    
    if wish_item:
        wish_item.delete() # Remove
        messages.info(request, 'Removed from Wishlist')
    else:
        Wishlist.objects.create(user=request.user, product=product) # Add
        messages.success(request, 'Added to Wishlist')
        
    # Redirect back to where they came from
    return redirect(request.META.get('HTTP_REFERER', 'pricing_sheet'))

@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user)
    return render(request, 'products/wishlist.html', {'items': items})

# --- FEATURE 5: PROFILE SETTINGS ---
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

# --- NEW: Cart Update Logic ---
def update_cart(request, item_id, action):
    cart = request.session.get('cart', {})
    
    if item_id in cart:
        item = cart[item_id]
        
        if action == 'increase':
            # Check stock availability before increasing
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
            # Remove if quantity becomes 0
            if cart[item_id]['quantity'] < 1:
                del cart[item_id]
                
        elif action == 'remove':
            del cart[item_id]
    
    request.session['cart'] = cart
    return redirect('view_cart')


# --- 2. THE NEW DASHBOARD VIEW ---
@login_required
def user_dashboard(request):
    user = request.user
    
    # 1. Handle Profile Update
    if request.method == 'POST' and 'update_profile' in request.POST:
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, instance=user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_dashboard')
            
    # 2. Handle Password Change
    elif request.method == 'POST' and 'change_password' in request.POST:
        password_form = PasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # Important! Keeps user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Please correct the error below.')
    
    # 3. Initial Load
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=user.profile)
        password_form = PasswordChangeForm(user)

    # Get recent orders for the dashboard widget
    recent_orders = Sale.objects.filter(user=user).order_by('-created_at')[:3]
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form,
        'recent_orders': recent_orders
    }
    return render(request, 'registration/dashboard.html', context)


# ... existing imports ...

def about_us(request):
    return render(request, 'products/about.html')

def contact_us(request):
    return render(request, 'products/contact.html')