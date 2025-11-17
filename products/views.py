from django.shortcuts import render, get_object_or_404, redirect
from .models import Product,ProductVariation, Sale, SaleItem  # Import your Product model
from django.http import HttpRequest

def pricing_sheet(request):
    # 1. Get all products from the database
    # We order them by name
    all_products = Product.objects.all().order_by('name')
    
    # 2. Put the data into a "context" dictionary
    # This is how we pass data from Python to HTML
    context = {
        'products': all_products,
    }
    
    # 3. "Render" the HTML page
    # This tells Django to take the 'products/pricing_sheet.html' template,
    # combine it with our 'context' data, and send it to the browser.
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


# --- ADD THIS CHECKOUT FUNCTION ---
def checkout(request: HttpRequest):
    # Get the cart from the session
    cart = request.session.get('cart', {})
    if not cart:
        # If the cart is empty, just redirect to the cart page
        return redirect('view_cart')

    if request.method == 'POST':
        # --- THIS IS THE ORDER PROCESSING LOGIC ---

        # 1. Create a new "Sale" (the "receipt")
        new_sale = Sale.objects.create()

        # 2. Loop through every item in the session cart
        for product_id, item_data in cart.items():

            # Get the main product
            # THIS IS THE CORRECT LINE
            product = get_object_or_404(Product, id=item_data['product_id'])
            
            variation = None
            if item_data['variation_id']:
                variation = get_object_or_404(ProductVariation, id=item_data['variation_id'])
            # 3. Create a "SaleItem" for this item
            SaleItem.objects.create(
                sale=new_sale,
                product=product,
                variation=variation,
                quantity=item_data['quantity'],
                sold_price=item_data['price'],
                # We are using the product's CURRENT buying_cost
                # A better app might store this in the session too
                buying_cost=product.buying_cost 
            )
            # NOTE: The save() method you wrote in models.py
            # is AUTOMATICALLY called here,
            # so your stock is updated!

        # 4. Clear the cart from the session
        request.session['cart'] = {}

        # 5. Redirect to a "success" page
        return redirect('order_success')

    # --- This is the GET request logic (just showing the page) ---
    # We re-use the logic from view_cart to show cart items
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
    }
    return render(request, 'products/checkout.html', context)


# --- ADD THIS SIMPLE SUCCESS VIEW ---
def order_success(request):
    return render(request, 'products/order_success.html')