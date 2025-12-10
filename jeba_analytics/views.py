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

import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import SessionTrace
from .analytics_service import AnalyticsService


@csrf_exempt
@require_POST
def ingest_beacon(request):
    """
    Lightning-fast endpoint for accepting telemetry blobs.
    """
    try:
        # 1. Parse Payload (Multipart or JSON)
        if request.content_type == 'application/json':
            payload = json.loads(request.body)
            # Normalize structure if sent purely as JSON
            data_blob = payload.get('data', {})
            session_id = payload.get('session_id')
            url = payload.get('url')
        else:
            # Beacon API sends FormData by default
            session_id = request.POST.get('session_id')
            url = request.POST.get('url')
            raw_data_str = request.POST.get('data')
            data_blob = json.loads(raw_data_str) if raw_data_str else {}

        if not session_id:
            return HttpResponse("No Session ID", status=400)

        # 2. Extract Key Metrics for Indexing
        perf = data_blob.get('performance', {})
        
        defaults = {
            'url': url,
            'ip_address': AnalyticsService.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:300],
            'device_type': AnalyticsService.get_device_info(request),
            
            # Fast access metrics
            'load_time_ms': perf.get('fullLoad'),
            'ttfb_ms': perf.get('ttfb'),
            'max_scroll': data_blob.get('max_scroll', 0),
            'is_bounce': data_blob.get('is_bounce', True),
            'duration_ms': data_blob.get('duration', 0),
            'raw_data': data_blob
        }

        # 3. Update or Create (Atomic)
        # We use update_or_create to handle multiple beacon pulses (heartbeats)
        SessionTrace.objects.update_or_create(
            session_id=session_id,
            defaults=defaults
        )

        return JsonResponse({'status': 'ok', 'trace': session_id})

    except Exception as e:
        # Log error internally but return 200 to not freak out the browser
        print(f"❌ Beacon Error: {str(e)}")
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)

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