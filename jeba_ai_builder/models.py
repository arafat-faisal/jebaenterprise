from django.db import models
from django.utils.text import slugify

class AIPage(models.Model):
    """
    Represents a single Landing Page managed entirely by AI.
    """
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    
    # --- NEW: Product Link ---
    product = models.ForeignKey(
        'jeba_inventory.Product', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='ai_pages',
        help_text="Link this page to a specific product to auto-fill content."
    )
    # -------------------------

    # The Living Code
    compiled_html = models.TextField(blank=True, help_text="The full, raw HTML of the page.")
    compiled_css = models.TextField(blank=True, help_text="Custom CSS specific to this page.")
    
    # Status
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class PageConversation(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('ai', 'AI Model'),
        ('system', 'System Context'),
    ]

    page = models.ForeignKey(AIPage, on_delete=models.CASCADE, related_name='conversation')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    
    # Inputs
    text_prompt = models.TextField(blank=True, null=True)
    reference_image = models.ImageField(upload_to='ai_builder/refs/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role} - {self.created_at.strftime('%H:%M:%S')}"

class PageVersion(models.Model):
    page = models.ForeignKey(AIPage, on_delete=models.CASCADE, related_name='versions')
    html_snapshot = models.TextField()
    css_snapshot = models.TextField(blank=True)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Version {self.id} - {self.description}"