from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# --- MODULAR IMPORTS ---
from jeba_inventory.models import Product
from jeba_engagement.models import Wishlist
# -----------------------

# --- LEGACY IMPORTS ---
# We are still using the form from the old location for now
from jeba_engagement.forms import ReviewForm 

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
        
    # Redirect to wherever the user clicked from (or home if unknown)
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user)
    return render(request, 'wishlist.html', {'items': items})