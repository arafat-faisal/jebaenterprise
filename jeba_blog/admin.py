from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import BlogPost

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'featured_image_preview',
        'product_count',
        'is_published', 
        'created_at', 
        'views'
    )
    list_editable = ('is_published',) # Allow toggling publish status directly
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'content', 'excerpt', 'meta_description')
    readonly_fields = ('created_at', 'updated_at', 'views', 'image_tag')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('products',)
    
    fieldsets = (
        ("📝 Content & Publishing", {
            # Use a tuple for created_at/updated_at to put them side-by-side
            'fields': ('title', 'slug', 'excerpt', 'content', 'is_published', 'views', ('created_at', 'updated_at')),
        }),
        ("🖼️ Media & Featured Image", {
            'fields': ('featured_image', 'image_tag'), # 'image_tag' is the preview field
        }),
        ("🔗 Product Linking", {
            'fields': ('products',),
            'description': "Select related products. This improves internal linking and SEO."
        }),
        ("🔎 SEO Metadata", {
            # New SEO fields added here
            'fields': ('meta_title', 'meta_description'), 
            'classes': ('collapse',), # Collapse this section by default to keep the main form clean
        }),
    )
    
    # Custom method to display image thumbnail in list and detail view
    def image_tag(self, obj):
        if obj.featured_image:
            return format_html('<img src="{}" style="width: 150px; height: auto; border-radius: 5px;"/>', obj.featured_image.url)
        return "-"
    image_tag.short_description = 'Image Preview'
    
    # Custom method for list display image
    def featured_image_preview(self, obj):
        if obj.featured_image:
            return format_html('<img src="{}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;"/>', obj.featured_image.url)
        return "-"
    featured_image_preview.short_description = 'Image'

    # Annotate queryset to count linked products efficiently
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            products_count=Count('products', distinct=True)
        )
        
    def product_count(self, obj):
        # Access the annotated field
        return obj.products_count
    product_count.short_description = 'Products Linked'
    product_count.admin_order_field = 'products_count'