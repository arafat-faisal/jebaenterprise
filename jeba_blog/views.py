from django.shortcuts import render, get_object_or_404
from .models import BlogPost

def blog_list(request):
    """Show all published blog posts."""
    posts = BlogPost.objects.filter(is_published=True)
    return render(request, 'jeba_blog/blog_list.html', {'posts': posts})

def blog_detail(request, slug):
    """Show single post and its attached products."""
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    
    # Simple view counter
    post.views += 1
    post.save(update_fields=['views'])

    context = {
        'post': post,
        'attached_products': post.products.filter(stock_quantity__gt=0)[:4] # Show top 4 linked items
    }
    return render(request, 'jeba_blog/blog_detail.html', context)