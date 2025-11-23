from django.shortcuts import get_object_or_404
from django.http import JsonResponse

# --- MODULAR IMPORTS ---
from jeba_inventory.models import Product
from jeba_analytics.models import ProductEvent
# -----------------------

def track_share(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=product_id)
        
        # Ensure session exists
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