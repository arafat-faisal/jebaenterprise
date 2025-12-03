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

    # --- AI GENERATION LOGIC (FIXED) ---
    def generate_ai_content(self):
        """Calls the dedicated Landing AI to populate sections."""
        
        # CHANGED: Import from LOCAL ai_generator, not jeba_seo
        from .ai_generator import generate_landing_content
        
        if not self.product: 
            return False
            
        # Get image helper
        image_path = None
        try:
            img_obj = self.product.main_image_obj 
            if img_obj and img_obj.image:
                image_path = img_obj.image.path
        except Exception: pass

        # 1. Fetch Content
        content = generate_landing_content(
            product_name=self.product.name,
            description=self.product.description,
            category=self.product.category.name if hasattr(self.product, 'category') and self.product.category else "General",
            image_path=image_path
        )
        
        if content:
            # 2. Clear old sections
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
                overlay_opacity='0.6'
            )
            
            # --- FEATURES GRID (Rendered as HTML in a Rich Text block) ---
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

            # --- STORY / DETAILS ---
            self.sections.create(
                section_type='TEXT_IMAGE_SPLIT',
                heading=content.get('story_heading', "Product Details"),
                description=content.get('story_content', ''),
                order=2,
                ai_generated=True,
                text_alignment='start',
                image=self.product.main_image_obj.image if self.product.main_image_obj else None
            )
            
            # --- FAQ (Accordion) ---
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

    page = models.ForeignKey(LandingPage, related_name='sections', on_delete=models.CASCADE)
    section_type = models.CharField(max_length=50, choices=SECTION_TYPES, default='TEXT_IMAGE_SPLIT')
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
    background_color = models.CharField(max_length=20, blank=True, null=True)
    background_gradient = models.CharField(max_length=200, blank=True, null=True)
    text_color = models.CharField(max_length=20, blank=True, null=True)
    overlay_opacity = models.CharField(max_length=5, default='0.4')
    # --- NEW: RESPONSIVE POSITIONING ---
    desktop_media_position = models.CharField(
        max_length=50, 
        default="50% 50%", 
        help_text="X Y coordinates for Desktop image focus (e.g. '50% 20%')"
    )
    mobile_media_position = models.CharField(
        max_length=50, 
        default="50% 50%", 
        help_text="X Y coordinates for Mobile image focus"
    )
    # -----------------------------------
    divider_top = models.CharField(max_length=20, default='NONE')
    divider_bottom = models.CharField(max_length=20, default='NONE')
    border_radius = models.IntegerField(default=0)
    
    # Media
    image = models.ImageField(upload_to='landing/images/', blank=True, null=True)
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