from django import template
from jeba_seo.ai_engine import get_seo_data
from jeba_seo.models import GlobalSEOSettings

register = template.Library()

@register.inclusion_tag('jeba_seo/meta_tags.html', takes_context=True)
def render_seo_meta(context):
    """
    Renders the SEO meta tags (title, description, schema).
    Automatically detects if there is an object (product/blog) in the context.
    """
    request = context.get('request')
    
    # Try to find a main object in the context
    obj = context.get('product') or context.get('blog_post') or context.get('object')
    
    # Determine page type for static pages based on URL name
    page_type = None
    if request and request.resolver_match:
        url_name = request.resolver_match.url_name
        if url_name in ['home', 'about', 'contact', 'login', 'register']:
            page_type = url_name
            
    # Get the data from our AI Engine
    seo_data = get_seo_data(request, obj=obj, page_type=page_type)
    
    # Also pass the Global Settings for the Logo/Schema
    global_settings = GlobalSEOSettings.objects.first()
    
    return {
        'seo_data': seo_data,
        'site_settings': global_settings,
        'request': request
    }