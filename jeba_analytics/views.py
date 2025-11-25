from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

# --- MODULAR IMPORTS ---
from jeba_inventory.models import Product
from jeba_analytics.models import ProductEvent
from jeba_analytics.analytics_service import AnalyticsService
# -----------------------

def track_share(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=product_id)
        
        if not request.session.session_key:
            request.session.save()
            
        ProductEvent.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key,
            event_type='SHARE',
            metadata=AnalyticsService.get_context(request)
        )
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
@require_POST
def track_interaction(request):
    """
    General purpose endpoint for tracking JS interactions like 
    'WhatsApp Click', 'Initiate Checkout', etc.
    Expects JSON: { "product_id": 123, "event_type": "CONTACT" }
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        event_type = data.get('event_type')
        
        if not product_id or not event_type:
            return JsonResponse({'error': 'Missing data'}, status=400)

        product = get_object_or_404(Product, pk=product_id)
        
        if not request.session.session_key:
            request.session.save()

        # Use the service to get full context
        metadata = AnalyticsService.get_context(request)
        
        # Merge any extra JS data sent from frontend
        if 'extra' in data:
            metadata.update(data['extra'])

        ProductEvent.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key,
            event_type=event_type,
            metadata=metadata
        )
        
        return JsonResponse({'status': 'recorded', 'event': event_type})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)