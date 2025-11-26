from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required

# --- MODULAR IMPORTS ---
from jeba_inventory.models import Product
from jeba_intelligence.models import CompetitorPrice, ScraperPreset
# -----------------------

# --- UTILS IMPORT ---
# Ideally, this utility function should move to this app later, 
# but for now we import it from the central utils file.
from jeba_intelligence.utils import fetch_competitor_data

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
        return render(request, 'jeba_intelligence/admin_scraper.html', context)

    # --- POST Request Logic ---
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # FEATURE 1: MANUAL PRICE SAVE
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

        # Call helper logic
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