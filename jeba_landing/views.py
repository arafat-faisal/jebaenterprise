from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import LandingPage, LandingSection, LandingTheme
from django.utils.dateparse import parse_datetime

def landing_page_list(request):
    """Shows a list of all active landing pages."""
    pages = LandingPage.objects.filter(is_published=True).order_by('-created_at')
    return render(request, 'jeba_landing/landing_list.html', {'pages': pages})

def landing_page_detail(request, slug):
    if request.user.is_superuser:
        page = get_object_or_404(LandingPage, slug=slug)
    else:
        page = get_object_or_404(LandingPage, slug=slug, is_published=True)
        
    sections = page.sections.all().order_by('order')
    
    context = {
        'page': page,
        'sections': sections,
        'product': page.product, 
    }
    return render(request, 'jeba_landing/landing_page.html', context)

@staff_member_required
def trigger_ai_generation(request, pk):
    page = get_object_or_404(LandingPage, pk=pk)
    if not page.product:
        messages.error(request, "❌ AI Error: Please select a Product first.")
        return redirect(f'/admin/jeba_landing/landingpage/{pk}/change/')
        
    try:
        if page.generate_ai_content():
            messages.success(request, f"✨ AI generated content for '{page.product.name}'!")
        else:
            messages.warning(request, "⚠️ AI could not generate content.")
    except Exception as e:
        messages.error(request, f"❌ Error: {str(e)}")
        
    return redirect(f'/admin/jeba_landing/landingpage/{pk}/change/')

# --- ADMIN LIVE PREVIEW ENGINE ---
@csrf_exempt 
@staff_member_required
def admin_preview(request):
    if request.method != 'POST':
        return HttpResponse("Preview requires POST data", status=405)

    # 1. Mock the Page Object (RESTORED FIELDS)
    page = LandingPage(
        title=request.POST.get('title', 'Preview Title'),
        
        # Design & Theme (Restored)
        theme_preset=request.POST.get('theme_preset'),
        override_primary_color=request.POST.get('override_primary_color'),
        override_accent_color=request.POST.get('override_accent_color'),
        custom_css=request.POST.get('custom_css'),
        font_heading=request.POST.get('font_heading', 'Montserrat'),
        font_body=request.POST.get('font_body', 'Open Sans'),
        
        stock_warning=int(request.POST.get('stock_warning', 0) or 0),
        meta_pixel_id=request.POST.get('meta_pixel_id', ''),
    )

    # 2. Mock Relations
    theme_id = request.POST.get('theme')
    if theme_id:
        try:
            page.theme = LandingTheme.objects.get(pk=theme_id)
        except LandingTheme.DoesNotExist: pass

    product_id = request.POST.get('product')
    if product_id:
        from jeba_inventory.models import Product
        try:
            page.product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist: pass

    # Countdown
    date_val = request.POST.get('countdown_end_0')
    time_val = request.POST.get('countdown_end_1')
    if date_val and time_val:
        try:
            page.countdown_end = parse_datetime(f"{date_val} {time_val}")
        except: pass
    
    # 3. Reconstruct Sections
    total_forms = int(request.POST.get('sections-TOTAL_FORMS', 0))
    sections = []

    for i in range(total_forms):
        if request.POST.get(f'sections-{i}-DELETE') == 'on':
            continue
            
        sec_type = request.POST.get(f'sections-{i}-section_type', 'TEXT_IMAGE_SPLIT')
        
        section = LandingSection(
            id=request.POST.get(f'sections-{i}-id'),
            section_type=sec_type,
            
            # --- NEW: Catch design_variant from POST data ---
            design_variant=request.POST.get(f'sections-{i}-design_variant', 'OVERLAY'),
            # ------------------------------------------------

            heading=request.POST.get(f'sections-{i}-heading'),
            subheading=request.POST.get(f'sections-{i}-subheading'),
            description=request.POST.get(f'sections-{i}-description'),
            button_text=request.POST.get(f'sections-{i}-button_text'),
            
            text_alignment=request.POST.get(f'sections-{i}-text_alignment', 'center'),
            overlay_opacity=request.POST.get(f'sections-{i}-overlay_opacity', '0.4'),
            background_color=request.POST.get(f'sections-{i}-background_color'),
            text_color=request.POST.get(f'sections-{i}-text_color'),
            padding_top=int(request.POST.get(f'sections-{i}-padding_top') or 80),
            padding_bottom=int(request.POST.get(f'sections-{i}-padding_bottom') or 80),
            
            video_url=request.POST.get(f'sections-{i}-video_url'),
            icon_class=request.POST.get(f'sections-{i}-icon_class'),
            
            # Position Data (Restored)
            desktop_media_position=request.POST.get(f'sections-{i}-desktop_media_position', '50% 50%'),
            mobile_media_position=request.POST.get(f'sections-{i}-mobile_media_position', '50% 50%'),
        )
        
        section.form_index = i 
        
        # Handle Images
        section_id = request.POST.get(f'sections-{i}-id')
        if section_id:
            try:
                original = LandingSection.objects.get(pk=section_id)
                section.image = original.image
                section.video_file = original.video_file
                section.trust_badge_image = getattr(original, 'trust_badge_image', None)
                section.image_2 = original.image_2
                section.image_3 = original.image_3
                section.image_4 = original.image_4
                section.image_5 = original.image_5
            except: pass
                
        sections.append(section)

    context = {
        'page': page,
        'sections': sections,
        'product': getattr(page, 'product', None),
        'preview_mode': True
    }
    return render(request, 'jeba_landing/landing_page.html', context)