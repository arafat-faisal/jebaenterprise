from django.shortcuts import render, get_object_or_404
from .models import Product  # Import your Product model

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