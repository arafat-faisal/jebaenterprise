from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import LandingPage, LandingSection

def landing_page_detail(request, slug):
    # Only show published pages unless you are superuser (for previewing)
    if request.user.is_superuser:
        page = get_object_or_404(LandingPage, slug=slug)
    else:
        page = get_object_or_404(LandingPage, slug=slug, is_published=True)
        
    # Get all sections sorted by the order you set in admin
    sections = page.sections.all()
    
    context = {
        'page': page,
        'sections': sections,
        'product': page.product, 
    }
    return render(request, 'jeba_landing/landing_page.html', context)


# --- ADMIN PREVIEW ENGINE ---
@csrf_exempt # CSRF handled by admin JS
def admin_preview(request):
    """
    Renders the landing page using raw POST data from the admin form.
    Does not save anything to the database.
    """
    if request.method != 'POST':
        return HttpResponse("Preview requires POST data", status=405)

    # 1. Mock the Page Object
    page = LandingPage(
        title=request.POST.get('title', 'Preview Title'),
        meta_pixel_id=request.POST.get('meta_pixel_id', ''),
    )
    
    # 2. Resolve Product (Real or Mock)
    product_id = request.POST.get('product')
    product = None
    
    if product_id:
        from jeba_inventory.models import Product
        try:
            product = Product.objects.get(pk=product_id)
        except (Product.DoesNotExist, ValueError):
            pass
            
    # CRITICAL FIX: If no product is selected yet, create a Dummy Product
    # This prevents 'NoReverseMatch' errors in the template
    if not product:
        class MockProduct:
            id = 1  # Dummy ID to satisfy URL patterns
            name = "Select a Product..."
            selling_price = 0.00
            main_image_obj = None
        product = MockProduct()

    # 3. Mock the Sections
    sections = []
    total_forms = int(request.POST.get('sections-TOTAL_FORMS', 0))
    
    for i in range(total_forms):
        # Skip deleted forms
        if request.POST.get(f'sections-{i}-DELETE') == 'on':
            continue
            
        sec_type = request.POST.get(f'sections-{i}-section_type', 'TEXT_IMAGE_SPLIT')
        
        section = LandingSection(
            section_type=sec_type,
            heading=request.POST.get(f'sections-{i}-heading'),
            subheading=request.POST.get(f'sections-{i}-subheading'),
            description=request.POST.get(f'sections-{i}-description'),
            background_color=request.POST.get(f'sections-{i}-background_color'),
            text_color=request.POST.get(f'sections-{i}-text_color'),
            video_url=request.POST.get(f'sections-{i}-video_url'),
        )
        
        # Try to restore existing image from DB if available
        # (Browsers don't send file content via JS preview fetch for security)
        section_id = request.POST.get(f'sections-{i}-id')
        if section_id:
            try:
                original = LandingSection.objects.get(pk=section_id)
                section.image = original.image
                section.video_file = original.video_file
            except:
                pass
                
        sections.append(section)

    # 4. Render
    context = {
        'page': page,
        'sections': sections,
        'product': product,
        'is_preview': True
    }
    
    return render(request, 'jeba_landing/landing_page.html', context)