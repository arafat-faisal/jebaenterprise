from django.contrib import admin
from .models import BlogPost

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'created_at', 'views')
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'content')
    
    # Auto-generate slug from title for SEO convenience
    prepopulated_fields = {'slug': ('title',)}
    
    # Easy widget to select multiple products
    filter_horizontal = ('products',)
    
    fieldsets = (
        ('SEO & Identity', {
            'fields': ('title', 'slug', 'excerpt', 'featured_image', 'is_published')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Product Linking', {
            'fields': ('products',),
            'description': "Attach products here. They will appear on the blog post, and this post will appear on their product pages."
        }),
    )