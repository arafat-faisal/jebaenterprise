from django.db import models
from django.utils.text import slugify

class LandingPage(models.Model):
    """
    A standalone landing page linked to a specific product.
    Designed for high-conversion ad campaigns.
    """
    title = models.CharField(max_length=255, help_text="Internal title for this campaign page")
    slug = models.SlugField(unique=True, max_length=255, help_text="URL path, e.g., 'super-sale-watch'")
    
    # Link to the actual product for pricing/checkout logic
    product = models.ForeignKey(
        'jeba_inventory.Product', 
        on_delete=models.CASCADE, 
        related_name='landing_pages'
    )
    
    # Marketing & Analytics
    meta_pixel_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Override the global pixel ID for this specific campaign"
    )
    
    # Status
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.slug})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class LandingSection(models.Model):
    """
    Modular sections that build up the landing page.
    Reorderable and highly visual.
    """
    SECTION_TYPES = [
        ('HERO', 'Hero Section (Full Screen)'),
        ('VIDEO', 'Cinematic Video'),
        ('FEATURES_GRID', 'Features Grid (Icons)'),
        ('TEXT_IMAGE_SPLIT', 'Split Content (Text + Image)'),
        ('CAROUSEL', 'Image Carousel (Slider)'),
    ]

    ANIMATION_EFFECTS = [
        ('NONE', 'No Animation'),
        ('FADE_UP', 'Fade In Up'),
        ('FADE_IN', 'Fade In Simple'),
        ('ZOOM_IN', 'Zoom In'),
        ('SLIDE_LEFT', 'Slide In from Left'),
        ('SLIDE_RIGHT', 'Slide In from Right'),
    ]

    # --- NEW: Alignment Options ---
    ALIGNMENT_CHOICES = [
        ('center', 'Center (Default)'),
        ('start', 'Left Aligned'),
        ('end', 'Right Aligned'),
    ]

    # --- NEW: Overlay Opacity Options ---
    OVERLAY_CHOICES = [
        ('0.0', 'No Overlay (Original Image)'),
        ('0.2', 'Light Shadow (20%)'),
        ('0.4', 'Medium Shadow (40% - Recommended)'),
        ('0.6', 'Dark Shadow (60%)'),
        ('0.8', 'Deep Shadow (80% - For Light Text)'),
    ]

    page = models.ForeignKey(
        LandingPage, 
        related_name='sections', 
        on_delete=models.CASCADE
    )
    
    # Configuration
    section_type = models.CharField(max_length=50, choices=SECTION_TYPES, default='TEXT_IMAGE_SPLIT')
    order = models.PositiveIntegerField(default=0, help_text="Order of appearance (0 is top)")
    
    # Content
    heading = models.CharField(max_length=255, blank=True, null=True)
    subheading = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True, help_text="Main text content for this section")
    
    # --- NEW: Button Control ---
    button_text = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Override the default button text (e.g. 'Get 50% Off'). Leave empty for default."
    )

    # --- NEW: Styling Controls ---
    text_alignment = models.CharField(
        max_length=20, 
        choices=ALIGNMENT_CHOICES, 
        default='center',
        help_text="Where should the text be positioned?"
    )
    overlay_opacity = models.CharField(
        max_length=5, 
        choices=OVERLAY_CHOICES, 
        default='0.4',
        help_text="Darkens the background image to make text readable."
    )
    
    # Media (Main)
    image = models.ImageField(
        upload_to='landing/images/', 
        blank=True, 
        null=True,
        help_text=(
            "<b>HERO GUIDE:</b> Recommended 1920x1080px (Landscape). "
            "If using 'Left Aligned' text, pick an image with space on the left. "
            "Use 'Overlay Opacity' to fix readability issues."
        )
    )
    video_file = models.FileField(upload_to='landing/videos/', blank=True, null=True, help_text="Upload MP4 for background or player")
    video_url = models.URLField(blank=True, null=True, help_text="YouTube/Vimeo link if not uploading file")
    
    # Extra Images for Carousel
    image_2 = models.ImageField(upload_to='landing/images/', blank=True, null=True, verbose_name="Carousel Image 2")
    image_3 = models.ImageField(upload_to='landing/images/', blank=True, null=True, verbose_name="Carousel Image 3")
    image_4 = models.ImageField(upload_to='landing/images/', blank=True, null=True, verbose_name="Carousel Image 4")
    image_5 = models.ImageField(upload_to='landing/images/', blank=True, null=True, verbose_name="Carousel Image 5")
    
    # Visuals
    background_color = models.CharField(max_length=20, default="#000000", help_text="Hex code (e.g. #000000)")
    text_color = models.CharField(max_length=20, default="#FFFFFF", help_text="Hex code (e.g. #FFFFFF)")
    animation_effect = models.CharField(max_length=20, choices=ANIMATION_EFFECTS, default='FADE_UP')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.get_section_type_display()} - {self.heading or 'Untitled'}"