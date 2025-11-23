from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Sum, Avg, Case, When, Value, IntegerField
from django.http import HttpResponse

# --- MODULAR IMPORTS ---
from jeba_inventory.models import Product, Category
from jeba_engagement.models import Wishlist
from jeba_analytics.models import ProductEvent, SearchEvent
from products.forms import ReviewForm # We will move forms later
# -----------------------

# --- HELPER: Get Recommendations ---
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
    
    if recent_events.count() < 3:
        return Product.objects.none()

    recent_category_ids = recent_events.order_by('-created_at')[:20].values_list('product__category_id', flat=True)

    if not recent_category_ids:
        return Product.objects.none()

    viewed_ids = recent_events.values_list('product_id', flat=True)
    recommendations = Product.objects.filter(category__id__in=recent_category_ids).exclude(id__in=viewed_ids).order_by('?')[:limit]
    return recommendations

# --- VIEWS ---

def pricing_sheet(request):
    """Homepage View"""
    featured_product = Product.objects.filter(is_featured=True).order_by('-created_at').first()
    if not featured_product:
        featured_product = Product.objects.order_by('-created_at').first()

    new_arrivals = Product.objects.order_by('-created_at')[:4]
    best_sellers = Product.objects.annotate(total_sold=Sum('saleitem__quantity')).order_by('-total_sold')[:4]
    recommendations = get_recommendations(request, limit=4)
    all_products = Product.objects.all().order_by('?')[:30]

    context = {
        'featured_product': featured_product,
        'new_arrivals': new_arrivals,
        'best_sellers': best_sellers,
        'recommendations': recommendations,
        'products': all_products,
    }
    return render(request, "products/pricing_sheet.html", context)

def product_catalog(request):
    products = Product.objects.all().prefetch_related('images')
    
    category_id = request.GET.get('category')
    sort_by = request.GET.get('sort')

    if category_id:
        products = products.filter(category_id=category_id)
    
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
        products = products.order_by('sort_priority', '-created_at')
        
    all_categories = Category.objects.all()
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

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    # TRACK VIEW
    if not request.session.session_key:
        request.session.save()
    ProductEvent.objects.create(
        product=product,
        user=request.user if request.user.is_authenticated else None,
        session_id=request.session.session_key,
        event_type='VIEW'
    )

    variations = product.variations.filter(is_active=True)
    
    related_products = Product.objects.filter(category=product.category).exclude(id=pk)[:12]
    if not related_products:
        related_products = Product.objects.exclude(id=pk).order_by('-created_at')[:12]

    reviews = product.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()
    
    # Recently Viewed Logic
    session_id = request.session.session_key
    user = request.user if request.user.is_authenticated else None
    history_qs = ProductEvent.objects.filter(event_type='VIEW').exclude(product_id=pk)
    if user:
        history_qs = history_qs.filter(user=user)
    else:
        history_qs = history_qs.filter(session_id=session_id)
    
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

def search_view(request):
    query = request.GET.get('q')
    products = Product.objects.all()
    
    if request.method == 'GET' and query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
        if not request.session.session_key: request.session.save()
        SearchEvent.objects.create(
            query=query,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key
        )

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
        'all_categories': all_categories,
        'active_category': category_id,
        'active_sort': sort_by
    }
    return render(request, 'products/search_results.html', context)

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

    context = {
        'products': products,
        'col_headers': col_headers,
        'cols_list': selected_cols_keys,
        'blank_cols_keys': blank_cols_keys,
        'all_cols': all_cols,
    }
    return render(request, 'products/print_page.html', context)