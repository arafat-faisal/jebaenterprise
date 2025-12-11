from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from jeba_inventory.models import Product
from jeba_seo.ai_engine import generate_product_content

from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.conf import settings


@staff_member_required
def generate_ai_for_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Get Image Path
    img_path = None
    if product.main_image_obj and product.main_image_obj.image:
        img_path = product.main_image_obj.image.path
        
    # Call AI
    data = generate_product_content(
        product.name, 
        product.description, 
        product.category.name if product.category else "General", 
        img_path
    )
    
    if data:
        product.ai_suggested_name = data.get('display_name')
        product.ai_suggested_short_description = data.get('short_description')
        product.ai_suggested_description = data.get('description')
        product.meta_title_ai = data.get('meta_title')
        product.meta_description_ai = data.get('meta_description')
        product.is_seo_optimized = True
        product.save()
        messages.success(request, f"AI Content Generated for {product.name}!")
    else:
        messages.error(request, "AI Generation Failed.")
        
    return redirect(request.META.get('HTTP_REFERER', '/admin/'))

@require_GET
def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /checkout/",
        "Disallow: /cart/",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")