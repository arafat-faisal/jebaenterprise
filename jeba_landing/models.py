from django.db import models
from django.utils.text import slugify
import json

# --- 1. THEME ENGINE ---
class LandingTheme(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    default_config = models.JSONField(default=dict, blank=True)
    base_css = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# --- 2. LANDING PAGE ---
class LandingPage(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    
    product = models.ForeignKey(
        'jeba_inventory.Product', 
        on_delete=models.CASCADE, 
        related_name='landing_pages'
    )
    
    # Theme & Design
    theme = models.ForeignKey(LandingTheme, on_delete=models.SET_NULL, null=True, blank=True)
    theme_preset = models.CharField(max_length=20, blank=True, null=True) 
    
    # Overrides
    override_primary_color = models.CharField(max_length=20, blank=True, null=True)
    override_accent_color = models.CharField(max_length=20, blank=True, null=True)
    custom_css = models.TextField(blank=True, null=True)
    
    # Fonts
    font_heading = models.CharField(max_length=50, default='Montserrat', blank=True)
    font_body = models.CharField(max_length=50, default='Open Sans', blank=True)

    # Conversion Tools
    countdown_end = models.DateTimeField(blank=True, null=True)
    stock_warning = models.IntegerField(default=0)
    trust_badge_image = models.ImageField(upload_to='landing/badges/', blank=True, null=True)
    
    # Meta
    meta_pixel_id = models.CharField(max_length=50, blank=True, null=True)
    is_published = models.BooleanField(default=False)
    ai_generated = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.slug})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    # --- AI GENERATION LOGIC ---
    def generate_ai_content(self):
        from .ai_generator import generate_landing_content
        
        if not self.product: 
            return False
            
        image_path = None
        try:
            img_obj = self.product.main_image_obj 
            if img_obj and img_obj.image:
                image_path = img_obj.image.path
        except Exception: pass

        content = generate_landing_content(
            product_name=self.product.name,
            description=self.product.description,
            category=self.product.category.name if hasattr(self.product, 'category') and self.product.category else "General",
            image_path=image_path
        )
        
        if content:
            self.sections.all().delete()
            
            # --- HERO ---
            self.sections.create(
                section_type='HERO',
                heading=content.get('hero_headline', self.product.name),
                subheading=content.get('hero_subhead', ''),
                button_text="Order Now - Limited Stock",
                order=0,
                ai_generated=True,
                image=self.product.main_image_obj.image if self.product.main_image_obj else None,
                overlay_opacity='0.6',
                design_variant='OVERLAY'
            )
            
            # --- FEATURES ---
            features_html = '<div class="row g-4">'
            for f in content.get('features', []):
                features_html += f'''
                <div class="col-md-6 col-lg-3 text-center">
                    <div class="p-4 border rounded-3 bg-opacity-10 bg-white h-100">
                        <i class="{f['icon']} fa-3x mb-3 text-warning"></i>
                        <h4 class="h5 fw-bold">{f['title']}</h4>
                        <p class="small opacity-75">{f['desc']}</p>
                    </div>
                </div>
                '''
            features_html += '</div>'

            self.sections.create(
                section_type='RICH_TEXT',
                heading="Why Customers Love This",
                description=features_html,
                order=1,
                ai_generated=True,
                padding_top=60,
                padding_bottom=60
            )

            # --- STORY ---
            self.sections.create(
                section_type='TEXT_IMAGE_SPLIT',
                heading=content.get('story_heading', "Product Details"),
                description=content.get('story_content', ''),
                order=2,
                ai_generated=True,
                text_alignment='start',
                image=self.product.main_image_obj.image if self.product.main_image_obj else None
            )
            
            # --- FAQ ---
            faq_html = '<div class="accordion" id="aiFaqAccordion">'
            for i, faq in enumerate(content.get('faqs', [])):
                faq_html += f'''
                <div class="accordion-item bg-transparent border-bottom border-secondary">
                    <h2 class="accordion-header">
                        <button class="accordion-button collapsed bg-transparent text-white shadow-none" type="button" data-bs-toggle="collapse" data-bs-target="#faq{i}">
                            {faq['question']}
                        </button>
                    </h2>
                    <div id="faq{i}" class="accordion-collapse collapse" data-bs-parent="#aiFaqAccordion">
                        <div class="accordion-body opacity-75">{faq['answer']}</div>
                    </div>
                </div>
                '''
            faq_html += '</div>'
            
            self.sections.create(
                section_type='RICH_TEXT',
                heading="Frequently Asked Questions",
                description=faq_html,
                order=3,
                ai_generated=True,
                background_color="#121212"
            )
            
            self.ai_generated = True
            self.save()
            return True
        return False

# --- 3. LANDING SECTIONS ---
class LandingSection(models.Model):
    SECTION_TYPES = [
        ('HERO', 'Hero Section'),
        ('VIDEO', 'Video Section'),
        ('FEATURES_GRID', 'Features Grid'),
        ('TEXT_IMAGE_SPLIT', 'Split Content'),
        ('CAROUSEL', 'Image Carousel'),
        ('RICH_TEXT', 'Rich Text Block'),
        ('TESTIMONIALS', 'Testimonials'),
        ('FAQ', 'FAQ Accordion'),
    ]

    DESIGN_VARIANTS = [
        ('OVERLAY', 'Full Screen Overlay (Default)'),
        ('SPLIT_LEFT', 'Split: Text Left / Image Right'),
        ('SPLIT_RIGHT', 'Split: Text Right / Image Left'),
        ('MINIMAL', 'Minimal Center (No Background Image)'),
        ('PRODUCT_FOCUS', 'Product Focus (Mobile First / Modern)'),
    ]

    page = models.ForeignKey(LandingPage, related_name='sections', on_delete=models.CASCADE)
    section_type = models.CharField(max_length=50, choices=SECTION_TYPES, default='TEXT_IMAGE_SPLIT')
    
    design_variant = models.CharField(
        max_length=50, 
        choices=DESIGN_VARIANTS, 
        default='OVERLAY',
        help_text="Controls the layout style"
    )

    order = models.PositiveIntegerField(default=0)
    
    # Content
    icon_class = models.CharField(max_length=100, blank=True, null=True)
    heading = models.CharField(max_length=255, blank=True, null=True)
    subheading = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    button_text = models.CharField(max_length=50, blank=True, null=True)
    
    # Design
    text_alignment = models.CharField(max_length=20, default='center')
    padding_top = models.IntegerField(default=80)
    padding_bottom = models.IntegerField(default=80)
    
    # --- NEW FIELD: TEXT PADDING ---
    text_content_padding = models.IntegerField(default=0, help_text="Padding around the text content (in pixels). Helps fix border issues.")
    
    background_color = models.CharField(max_length=20, blank=True, null=True)
    background_gradient = models.CharField(max_length=200, blank=True, null=True)
    text_color = models.CharField(max_length=20, blank=True, null=True)
    overlay_opacity = models.CharField(max_length=5, default='0.4')
    
    desktop_media_position = models.CharField(max_length=50, default="50% 50%")
    mobile_media_position = models.CharField(max_length=50, default="50% 50%")

    divider_top = models.CharField(max_length=20, default='NONE')
    divider_bottom = models.CharField(max_length=20, default='NONE')
    border_radius = models.IntegerField(default=0)
    
    # Media Assets
    image = models.ImageField(upload_to='landing/images/', blank=True, null=True, help_text="Background Image for Hero, or Side Image for Split.")
    
    foreground_image = models.ImageField(upload_to='landing/foreground/', blank=True, null=True, help_text="Custom Image/GIF to layer ON TOP of the background. Overrides product image.")
    foreground_video = models.FileField(upload_to='landing/foreground/', blank=True, null=True, help_text="Custom Video (MP4) to layer ON TOP of the background. Overrides images.")

    video_file = models.FileField(upload_to='landing/videos/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    
    # Carousel
    image_2 = models.ImageField(upload_to='landing/images/', blank=True, null=True)
    image_3 = models.ImageField(upload_to='landing/images/', blank=True, null=True)
    image_4 = models.ImageField(upload_to='landing/images/', blank=True, null=True)
    image_5 = models.ImageField(upload_to='landing/images/', blank=True, null=True)
    
    animation_effect = models.CharField(max_length=20, default='FADE_UP')
    ai_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.get_section_type_display()} - {self.heading}"