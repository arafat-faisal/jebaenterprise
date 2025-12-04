from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.crypto import get_random_string
from .models import AIPage, PageConversation, PageVersion
from .ai_service import generate_page_update
from jeba_inventory.models import Product 

@staff_member_required
def builder_workspace(request, slug=None):
    if not slug:
        unique_id = get_random_string(length=6)
        new_page = AIPage.objects.create(title=f"Untitled Draft {unique_id}")
        return redirect('ai_builder_workspace', slug=new_page.slug)

    page = get_object_or_404(AIPage, slug=slug)
    
    # Handle Product Linking
    if request.method == "POST" and 'link_product_id' in request.POST:
        p_id = request.POST.get('link_product_id')
        if p_id:
            page.product = Product.objects.get(id=p_id)
            page.save()
            return redirect('ai_builder_workspace', slug=page.slug)

    history = page.conversation.all().order_by('created_at')
    
    # Fetch all products for the dropdown
    products = Product.objects.filter(is_active=True).only('id', 'name')

    context = {
        'page': page,
        'history': history,
        'products': products,
    }
    return render(request, 'jeba_ai_builder/builder.html', context)

@staff_member_required
@csrf_exempt
def publish_page(request, slug):
    """
    Publishes the page so it is visible to the public.
    """
    if request.method == "POST":
        page = get_object_or_404(AIPage, slug=slug)
        page.is_published = True
        page.save()
        return JsonResponse({"status": "success", "message": "Page is now LIVE!"})
    return JsonResponse({"error": "Invalid method"}, status=400)

@staff_member_required
def restore_version(request, version_id):
    """
    Restores the page state to a specific previous version.
    """
    version = get_object_or_404(PageVersion, id=version_id)
    page = version.page
    
    # 1. Create a NEW snapshot of the CURRENT state (before we overwrite it)
    PageVersion.objects.create(
        page=page,
        html_snapshot=page.compiled_html,
        css_snapshot=page.compiled_css,
        description=f"Auto-Backup before restoring Version #{version.id}"
    )
    
    # 2. Overwrite current page
    page.compiled_html = version.html_snapshot
    page.compiled_css = version.css_snapshot
    page.save()
    
    # 3. Add to chat history
    PageConversation.objects.create(
        page=page,
        role='system',
        text_prompt=f"♻️ Restored version from {version.created_at.strftime('%H:%M')}"
    )
    
    return redirect('ai_builder_workspace', slug=page.slug)

@xframe_options_exempt 
def page_preview(request, slug):
    """
    Renders the raw HTML of the page. 
    Allowed to be shown inside an iframe.
    """
    page = get_object_or_404(AIPage, slug=slug)
    
    if not page.is_published and not request.user.is_staff:
        return render(request, '404.html', status=404)

    return render(request, 'jeba_ai_builder/preview_clean.html', {'page': page})

@staff_member_required
@csrf_exempt
def ai_chat_endpoint(request, slug):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    page = get_object_or_404(AIPage, slug=slug)
    
    prompt = request.POST.get('prompt')
    image_file = request.FILES.get('image')
    
    if not prompt and not image_file:
        return JsonResponse({"error": "Empty input"}, status=400)

    user_msg = PageConversation.objects.create(
        page=page,
        role='user',
        text_prompt=prompt,
        reference_image=image_file
    )

    image_path = user_msg.reference_image.path if user_msg.reference_image else None

    # --- PREPARE PRODUCT DATA ---
    product_context = None
    if page.product:
        p = page.product
        
        # FIX: Safe Image Access
        img_url = ""
        try:
            # Check if main_image_obj exists and has an image
            if hasattr(p, 'main_image_obj') and p.main_image_obj and p.main_image_obj.image:
                img_url = p.main_image_obj.image.url
        except Exception:
            pass
            
        product_context = f"""
        Product Name: {p.name}
        Price: {p.selling_price} (Original: {p.original_price})
        Description: {p.description}
        Main Image URL: {img_url}
        """
        # Append instruction to usage image if valid
        if img_url and not image_path:
             prompt += f" (IMPORTANT: Include the product image at {img_url})"
    # ---------------------------------

    result = generate_page_update(
        current_html=page.compiled_html,
        current_css=page.compiled_css,
        user_prompt=prompt,
        image_path=image_path,
        product_context=product_context 
    )

    if result:
        PageVersion.objects.create(
            page=page,
            html_snapshot=page.compiled_html,
            css_snapshot=page.compiled_css,
            description=f"Before: {prompt[:30]}..." if prompt else "Image update"
        )

        page.compiled_html = result.get('html', '')
        page.compiled_css = result.get('css', '')
        page.save()

        PageConversation.objects.create(
            page=page,
            role='ai',
            text_prompt=result.get('explanation', 'Page updated.')
        )

        return JsonResponse({
            "status": "success",
            "explanation": result.get('explanation')
        })

    return JsonResponse({"error": "AI failed to generate response"}, status=500)