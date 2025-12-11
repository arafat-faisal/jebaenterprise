from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from jeba_inventory.models import Product, Category
from jeba_blog.models import BlogPost

class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        # Only show active products
        return Product.objects.filter(is_active=True).order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        # ASSUMPTION: Your URL name is 'product_detail' and uses 'pk'
        return reverse('product_detail', args=[obj.pk])

class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        # ASSUMPTION: Your URL name is 'category_detail' or similar. 
        # If you filter by category in catalog, adjust this:
        # Example: /catalog/?category=electronics
        return f"/catalog/?category={obj.name}"

class BlogPostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # Assuming you have a 'published' status or similar
        return BlogPost.objects.all().order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at
        
    def location(self, obj):
        return reverse('blog_detail', args=[obj.slug])

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "monthly"

    def items(self):
        return ['home', 'about', 'contact', 'login', 'register']

    def location(self, item):
        return reverse(item)