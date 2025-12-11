import json
from django import template
from django.utils.safestring import mark_safe
from jeba_seo.ai_engine import get_seo_data
from jeba_seo.models import GlobalSEOSettings

register = template.Library()

def build_schema(request, obj, global_settings):
    site_url = request.build_absolute_uri('/')[:-1]
    schema_list = [{
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": global_settings.site_name,
        "url": site_url,
        "logo": site_url + global_settings.default_social_image.url if global_settings.default_social_image else "",
        "sameAs": []
    }]

    # 2. Product Schema
    if hasattr(obj, 'selling_price') and hasattr(obj, 'stock_quantity'):
        product_url = request.build_absolute_uri(obj.get_absolute_url()) if hasattr(obj, 'get_absolute_url') else request.build_absolute_uri()
        
        # IMAGE LOGIC (Improved)
        image_url = ""
        if hasattr(obj, 'main_image_obj') and obj.main_image_obj:
            image_url = request.build_absolute_uri(obj.main_image_obj.image.url)
        elif hasattr(obj, 'thumbnail') and obj.thumbnail:
             image_url = request.build_absolute_uri(obj.thumbnail.url)

        # DESCRIPTION LOGIC (AI Aware)
        # 1. Manual Override -> 2. AI Generated -> 3. Product Description -> 4. Fallback
        final_description = getattr(obj, 'meta_description', '') or \
                            getattr(obj, 'meta_description_ai', '') or \
                            getattr(obj, 'short_description', '') or \
                            "Product from " + global_settings.site_name

        availability = "https://schema.org/InStock" if obj.stock_quantity > 0 else "https://schema.org/OutOfStock"

        product_schema = {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": getattr(obj, 'display_name', obj.name), # Use display_name property if available
            "image": image_url,
            "description": final_description,
            "sku": str(obj.id),
            "brand": {
                "@type": "Brand",
                "name": global_settings.site_name
            },
            "offers": {
                "@type": "Offer",
                "url": product_url,
                "priceCurrency": "BDT",
                "price": str(obj.selling_price),
                "availability": availability,
                "itemCondition": "https://schema.org/NewCondition"
            }
        }
        schema_list.append(product_schema)
        
        # Breadcrumb
        if hasattr(obj, 'category') and obj.category:
            breadcrumb = {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Home",
                        "item": site_url
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": obj.category.name,
                        "item": site_url + "/category/" + obj.category.name 
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": obj.name,
                        "item": product_url
                    }
                ]
            }
            schema_list.append(breadcrumb)

    # 3. Blog Post Schema
    elif hasattr(obj, 'title') and hasattr(obj, 'content'): 
        article_schema = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": obj.title,
            "image": request.build_absolute_uri(obj.featured_image.url) if obj.featured_image else "",
            "author": {
                "@type": "Person",
                "name": "Admin"
            },
            "publisher": {
                "@type": "Organization",
                "name": global_settings.site_name,
                "logo": {
                    "@type": "ImageObject",
                    "url": site_url + global_settings.default_social_image.url if global_settings.default_social_image else ""
                }
            },
            "datePublished": obj.created_at.isoformat() if hasattr(obj, 'created_at') else "",
        }
        schema_list.append(article_schema)

    return schema_list

@register.inclusion_tag('jeba_seo/meta_tags.html', takes_context=True)
def render_seo_meta(context):
    request = context.get('request')
    obj = context.get('product') or context.get('blog_post') or context.get('object')
    
    page_type = None
    if request and request.resolver_match:
        url_name = request.resolver_match.url_name
        if url_name in ['home', 'about', 'contact', 'login', 'register']:
            page_type = url_name
            
    seo_data = get_seo_data(request, obj=obj, page_type=page_type)
    
    global_settings = GlobalSEOSettings.objects.first()
    if not global_settings:
        global_settings = GlobalSEOSettings(site_name="Jeba Enterprise")

    json_ld_list = build_schema(request, obj, global_settings)
    json_ld_output = mark_safe(json.dumps(json_ld_list))

    return {
        'seo_data': seo_data,
        'site_settings': global_settings,
        'json_ld_output': json_ld_output, 
        'request': request
    }