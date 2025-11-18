from django.shortcuts import render, get_object_or_404, redirect
from .models import Product,ProductVariation, Sale, SaleItem, ProductImage,  CompetitorPrice,Category   # Import your Product model
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

def pricing_sheet(request):
        # 1. Start with all products (and prefetch related data)
        all_products = Product.objects.prefetch_related('images', 'variations').all()
        
        # 2. Get Search Query (q) and Category Filter
        search_query = request.GET.get('q')
        category_id = request.GET.get('category')

        # 3. Apply Filters
        if search_query:
            # Filter products where name OR description contains the query
            all_products = all_products.filter(
                Q(name__icontains=search_query) | Q(description__icontains=search_query)
            )
            
        if category_id:
            all_products = all_products.filter(category_id=category_id)

        # 4. Final Product Ordering
        all_products = all_products.order_by('name')

        # 5. Get all Categories for the filter bar
        all_categories = Category.objects.all().order_by('name')

        # 6. Pass data to the template
        context = {
            'products': all_products,
            'all_categories': all_categories,
            'active_category': category_id # Pass this to highlight the active filter
        }
        
        return render(request, "products/pricing_sheet.html", context)


# --- ADD THIS NEW FUNCTION ---
def product_detail(request, pk):
    # pk is the product ID passed from the URL
    # 1. Get the single product from the database
    # get_object_or_404 is a shortcut to get a product or show a "Not Found" page
    product = get_object_or_404(Product, pk=pk)
    
    # 2. Get all the variations that BELONG to this product
    variations = product.variations.filter(is_active=True)
    
    # 3. Put them into the context
    context = {
        'product': product,
        'variations': variations,
    }
    
    # 4. Render the new HTML template
    return render(request, "products/product_detail.html", context)

# --- THIS IS YOUR MODIFIED 'add_to_cart' FOR MAIN PRODUCTS ---
def add_to_cart(request: HttpRequest, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))

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
    return redirect('product_detail', pk=product_id)

# --- THIS IS THE NEW 'add_to_cart_variation' FUNCTION ---
def add_to_cart_variation(request: HttpRequest, variation_id):
    variation = get_object_or_404(ProductVariation, id=variation_id)
    product = variation.product # Get the parent product
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))

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
    # Get the cart from the session
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('view_cart')

    if request.method == 'POST':
        # --- PROCESS THE FORM ---
        form = CheckoutForm(request.POST)
        
        if form.is_valid():
            # 1. Create the Sale object but don't save to DB yet (commit=False)
            new_sale = form.save(commit=False)
            
            # 2. Associate with logged-in user (if they are logged in)
            if request.user.is_authenticated:
                new_sale.user = request.user
            
            # 3. Now save it to get an ID
            new_sale.save()

            # 4. Loop through every item in the session cart
            for product_id, item_data in cart.items():
                # Logic to handle both standard products and variations
                product_id_clean = item_data['product_id']
                product = get_object_or_404(Product, id=product_id_clean)
                
                variation = None
                if item_data['variation_id']:
                    variation = get_object_or_404(ProductVariation, id=item_data['variation_id'])
                
                SaleItem.objects.create(
                    sale=new_sale,
                    product=product,
                    variation=variation,
                    quantity=item_data['quantity'],
                    sold_price=item_data['price'],
                    buying_cost=product.buying_cost 
                )

            # 5. Clear the cart and redirect
            request.session['cart'] = {}
            return redirect('order_success')

    else:
        # --- GET REQUEST: Pre-fill the form ---
        initial_data = {}
        if request.user.is_authenticated:
            # Auto-fill name if logged in
            initial_data['customer_name'] = f"{request.user.first_name} {request.user.last_name}".strip()
            
        form = CheckoutForm(initial=initial_data)

    # --- Calculate Totals for Display ---
    cart_items = []
    total_price = 0
    for product_id, item_data in cart.items():
        item_total = item_data['price'] * item_data['quantity']
        cart_items.append({
            'name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity'],
            'item_total': item_total,
        })
        total_price += item_total

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'form': form, # We pass the form to the template here
    }
    return render(request, 'products/checkout.html', context)

# --- ADD THIS SIMPLE SUCCESS VIEW ---
def order_success(request):
    return render(request, 'products/order_success.html')


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
        'selling_price': 'Base Price', # Renamed from "Selling Price"
        'variations': 'Price Variations', # NEW
        'competitor_prices': 'Competitor Prices', # NEW
        'box_quantity': 'Box Quantity',
        'stock': 'Stock',
    }
    
    # Get the list of checked boxes from the URL
    # request.GET.getlist('cols') gets all values checked with name="cols"
    selected_cols_keys = request.GET.getlist('cols')
    
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
        # Create a form instance from the posted data
        form = UserCreationForm(request.POST)
        if form.is_valid():
            # Save the new user and log a success message
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login') # Redirects to the login page (built-in)
    else:
        # Create a blank form for a GET request
        form = UserCreationForm()

    context = {'form': form}
    return render(request, 'registration/register.html', context)


# --- ADD THIS NEW FUNCTION ---
# This decorator prevents anyone who isn't logged in from seeing the page
@login_required
def my_orders_view(request):
    # Filter Sales to ONLY show the ones belonging to the current user
    user_orders = Sale.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'orders': user_orders
    }
    return render(request, 'registration/my_orders.html', context)

@login_required
def order_detail(request, pk):
    # 1. Get the sale object (receipt) by its ID (pk)
    sale = get_object_or_404(Sale, pk=pk)

    # 2. SECURITY CHECK: Ensure the logged-in user is the one who made this order.
    # If someone tries to guess an ID (e.g., /order/5/) that isn't theirs, kick them out.
    if sale.user != request.user:
        return redirect('my_orders')

    # 3. Render the receipt page
    context = {
        'sale': sale
    }
    return render(request, 'products/order_detail.html', context)