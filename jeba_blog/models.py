from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.urls import reverse
from django.conf import settings

# --- MODULAR IMPORT ---
from jeba_inventory.models import Product

class BlogPost(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Blog Title"))
    slug = models.SlugField(
        max_length=255, 
        unique=True, 
        help_text=_("URL-friendly version of the title (auto-generated). Essential for SEO.")
    )
    
    # --- NEW: SEO Fields ---
    meta_title = models.CharField(
        max_length=150, 
        blank=True, 
        help_text=_("Custom title tag for search results (max 60 chars recommended).")
    )
    meta_description = models.CharField(
        max_length=255, 
        blank=True, 
        help_text=_("Custom meta description for search results (max 155 chars recommended).")
    )
    # -----------------------
    
    # --- CONTENT ---
    featured_image = models.ImageField(upload_to='blog/featured/', blank=True, null=True)
    content = models.TextField(verbose_name=_("Post Content"))
    excerpt = models.TextField(
        max_length=500, 
        blank=True, 
        help_text=_("Short summary for SEO meta descriptions and list views. Will auto-fill if empty.")
    )

    # --- INTELLIGENT LINKING ---
    products = models.ManyToManyField(
        Product, 
        blank=True, 
        related_name='blog_posts',
        verbose_name=_("Attached Products"),
        help_text=_("Select products mentioned in this post to create backlinks.")
    )

    # --- META ---
    is_published = models.BooleanField(default=True, verbose_name=_("Published"))
    views = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'jeba_blog_post'
        ordering = ['-created_at']
        verbose_name = _("Blog Post")
        verbose_name_plural = _("Blog Posts")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        
        # NEW: Auto-fill meta title if blank
        if not self.meta_title:
            self.meta_title = self.title
        
        # NEW: Auto-fill excerpt from content if blank
        if not self.excerpt and self.content:
            self.excerpt = self.content[:160] # Use a shorter length for a safer meta description fallback
            
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog_detail', args=[self.slug])