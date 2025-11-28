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
        # We need a dummy product to prevent template errors if product is accessed
        # In a real scenario, we might try to fetch the actual product if 'product' ID is passed
    )

    # 2. Try to fetch the real Linked Product to show real prices/images in preview
    product_id = request.POST.get('product')
    if product_id:
        from jeba_inventory.models import Product
        try:
            page.product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            pass

    # 3. Reconstruct Sections from Inline Form Data
    total_forms = int(request.POST.get('sections-TOTAL_FORMS', 0))
    sections = []

    for i in range(total_forms):
        # Skip deleted forms
        if request.POST.get(f'sections-{i}-DELETE') == 'on':
            continue
            
        sec_type = request.POST.get(f'sections-{i}-section_type', 'TEXT_IMAGE_SPLIT')
        
        # --- UPDATED: Now capturing the new fields ---
        section = LandingSection(
            id=request.POST.get(f'sections-{i}-id'), # Keep ID to find images later
            section_type=sec_type,
            heading=request.POST.get(f'sections-{i}-heading'),
            subheading=request.POST.get(f'sections-{i}-subheading'),
            description=request.POST.get(f'sections-{i}-description'),
            
            # New Content Fields
            button_text=request.POST.get(f'sections-{i}-button_text'),
            
            # New Design Fields
            text_alignment=request.POST.get(f'sections-{i}-text_alignment', 'center'),
            overlay_opacity=request.POST.get(f'sections-{i}-overlay_opacity', '0.4'),
            
            # Colors
            background_color=request.POST.get(f'sections-{i}-background_color'),
            text_color=request.POST.get(f'sections-{i}-text_color'),
            
            # Media Links
            video_url=request.POST.get(f'sections-{i}-video_url'),
        )
        
        # 4. Handle Images (Browsers don't send file content via JS preview fetch security)
        # We try to load the existing image from the DB if the section already exists.
        section_id = request.POST.get(f'sections-{i}-id')
        if section_id:
            try:
                original = LandingSection.objects.get(pk=section_id)
                section.image = original.image
                section.video_file = original.video_file
                # Restore Carousel Images
                section.image_2 = original.image_2
                section.image_3 = original.image_3
                section.image_4 = original.image_4
                section.image_5 = original.image_5
            except:
                pass
                
        sections.append(section)

    # 5. Render using the same template as the live site
    context = {
        'page': page,
        'sections': sections,
        'product': getattr(page, 'product', None),
    }
    return render(request, 'jeba_landing/landing_page.html', context)