from django.db import models
from django.utils.text import slugify

class LandingPage(models.Model):
    """
    A standalone landing page linked to a specific product.
    Acts as the 'Theme Controller' for the entire page.
    """
    FONT_CHOICES = [
        ('Montserrat', 'Montserrat (Modern & Bold)'),
        ('Open Sans', 'Open Sans (Clean & Neutral)'),
        ('Roboto', 'Roboto (Tech & Sharp)'),
        ('Playfair Display', 'Playfair Display (Luxury & Serif)'),
        ('Lato', 'Lato (Friendly)'),
        ('Oswald', 'Oswald (Strong Headers)'),
        ('Raleway', 'Raleway (Elegant)'),
    ]

    title = models.CharField(max_length=255, help_text="Internal title for this campaign page")
    slug = models.SlugField(unique=True, max_length=255, help_text="URL path, e.g., 'super-sale-watch'")
    
    # Link to the actual product for pricing/checkout logic
    product = models.ForeignKey(
        'jeba_inventory.Product', 
        on_delete=models.CASCADE, 
        related_name='landing_pages'
    )
    
    # --- GLOBAL THEME SETTINGS ---
    font_heading = models.CharField(max_length=50, choices=FONT_CHOICES, default='Montserrat', help_text="Font for Headlines")
    font_body = models.CharField(max_length=50, choices=FONT_CHOICES, default='Open Sans', help_text="Font for regular text")
    
    # Color Palette
    primary_color = models.CharField(max_length=20, default="#000000", help_text="Main Background Color")
    secondary_color = models.CharField(max_length=20, default="#1d1d1f", help_text="Card/Section Background Color")
    accent_color = models.CharField(max_length=20, default="#D4F759", help_text="Buttons, Icons, and Highlights")
    text_color = models.CharField(max_length=20, default="#FFFFFF", help_text="Global Text Color")

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
    Modular sections with high-level design customization.
    """
    SECTION_TYPES = [
        ('HERO', 'Hero Section (Full Screen)'),
        ('VIDEO', 'Cinematic Video'),
        ('FEATURES_GRID', 'Features Grid (Icons)'),
        ('TEXT_IMAGE_SPLIT', 'Split Content (Text + Image)'),
        ('CAROUSEL', 'Image Carousel (Slider)'),
        ('RICH_TEXT', 'Rich Text / HTML Block'),
    ]

    ANIMATION_EFFECTS = [
        ('NONE', 'No Animation'),
        ('FADE_UP', 'Fade In Up'),
        ('FADE_IN', 'Fade In Simple'),
        ('ZOOM_IN', 'Zoom In'),
        ('SLIDE_LEFT', 'Slide In from Left'),
        ('SLIDE_RIGHT', 'Slide In from Right'),
    ]

    ALIGNMENT_CHOICES = [
        ('center', 'Center (Default)'),
        ('start', 'Left Aligned'),
        ('end', 'Right Aligned'),
    ]
    
    # New: Shape Dividers for visual flow
    SHAPE_DIVIDERS = [
        ('NONE', 'None'),
        ('WAVE', 'Organic Wave'),
        ('SLANT_RIGHT', 'Sharp Slant (Right)'),
        ('SLANT_LEFT', 'Sharp Slant (Left)'),
        ('CURVE', 'Smooth Curve'),
        ('ARROW', 'Arrow Down'),
    ]

    page = models.ForeignKey(
        LandingPage, 
        related_name='sections', 
        on_delete=models.CASCADE
    )
    
    # Configuration
    section_type = models.CharField(max_length=50, choices=SECTION_TYPES, default='TEXT_IMAGE_SPLIT')
    order = models.PositiveIntegerField(default=0, help_text="Order of appearance (0 is top)")
    
    # --- CONTENT ---
    icon_class = models.CharField(max_length=100, blank=True, null=True, help_text="FontAwesome class (e.g., 'fa-solid fa-rocket')")
    heading = models.CharField(max_length=255, blank=True, null=True)
    subheading = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True, help_text="Main text content for this section")
    button_text = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Override button text (e.g. 'Get 50% Off'). Leave empty for default."
    )

    # --- DESIGN FREEDOM ---
    # Layout
    text_alignment = models.CharField(max_length=20, choices=ALIGNMENT_CHOICES, default='center')
    padding_top = models.IntegerField(default=80, help_text="Padding Top (px)")
    padding_bottom = models.IntegerField(default=80, help_text="Padding Bottom (px)")
    
    # Colors & Backgrounds
    background_color = models.CharField(max_length=20, blank=True, null=True, help_text="Hex Color (Overrides Global)")
    background_gradient = models.CharField(max_length=200, blank=True, null=True, help_text="CSS Gradient (e.g., 'linear-gradient(45deg, #ff0000, #0000ff)')")
    text_color = models.CharField(max_length=20, blank=True, null=True, help_text="Text Color (Overrides Global)")
    overlay_opacity = models.CharField(
        max_length=5, 
        default='0.4',
        choices=[('0.0','0%'),('0.2','20%'),('0.4','40%'),('0.6','60%'),('0.8','80%'),('0.9','90%')],
        help_text="Darkens background image for readability."
    )
    
    # Shapes & Visuals
    divider_top = models.CharField(max_length=20, choices=SHAPE_DIVIDERS, default='NONE', help_text="Shape separator at the top")
    divider_bottom = models.CharField(max_length=20, choices=SHAPE_DIVIDERS, default='NONE', help_text="Shape separator at the bottom")
    border_radius = models.IntegerField(default=0, help_text="Round corners for inner cards/images (px)")
    
    # Media (Main)
    image = models.ImageField(upload_to='landing/images/', blank=True, null=True)
    video_file = models.FileField(upload_to='landing/videos/', blank=True, null=True, help_text="Upload MP4")
    video_url = models.URLField(blank=True, null=True, help_text="YouTube/Vimeo link")
    
    # Carousel Images
    image_2 = models.ImageField(upload_to='landing/images/', blank=True, null=True, verbose_name="Carousel Image 2")
    image_3 = models.ImageField(upload_to='landing/images/', blank=True, null=True, verbose_name="Carousel Image 3")
    image_4 = models.ImageField(upload_to='landing/images/', blank=True, null=True, verbose_name="Carousel Image 4")
    image_5 = models.ImageField(upload_to='landing/images/', blank=True, null=True, verbose_name="Carousel Image 5")
    
    animation_effect = models.CharField(max_length=20, choices=ANIMATION_EFFECTS, default='FADE_UP')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.get_section_type_display()} - {self.heading or 'Untitled'}"