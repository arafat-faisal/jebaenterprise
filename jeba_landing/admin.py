from django.contrib import admin
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import redirect
from .models import Campaign, CampaignVariant, LandingSection, VisitorSession, ConversionEvent
from django.contrib import messages
from .ai_service import generate_landing_copy

# --- INLINES ---

class LandingSectionInline(admin.StackedInline):
    model = LandingSection
    extra = 1 # Show at least one empty form
    sortable_field_name = "order"
    # Removed 'collapse' class to make it visible by default
    fieldsets = (
        (None, {
            'fields': ('section_type', 'order', 'is_dark_mode', 'padding_y')
        }),
        ('Content (JSON)', {
            'fields': ('content',),
            'classes': ('collapse',),
        }),
    )

class CampaignVariantInline(admin.StackedInline):
    model = CampaignVariant
    extra = 0
    show_change_link = True
    fields = ('name', 'weight', 'primary_color', 'accent_color', 'enable_fomo_timer', 'enable_social_proof')

# --- MAIN ADMINS ---

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('title', 'product', 'is_active', 'slug')}),
        ('AI & Automation', {'fields': ('manual_ai_prompt',), 'description': 'Paste JSON from external AI to auto-generate content.'}),
        ('Localization', {'fields': ('currency', 'language_toggle')}),
        ('SEO', {'fields': ('meta_title', 'meta_description', 'meta_pixel_id')}),
    )
    list_display = ('title', 'product', 'is_active', 'view_dashboard_link') # <--- Added Dashboard Link
    inlines = [CampaignVariantInline]
    actions = ['generate_ai_content', 'generate_external_prompt']

    def generate_external_prompt(self, request, queryset):
        """
        Generates a copy-pasteable prompt for external AI tools.
        """
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one campaign.", level=messages.ERROR)
            return
            
        campaign = queryset.first()
        product = campaign.product
        
        if not product:
            self.message_user(request, "Campaign must strictly have a product.", level=messages.ERROR)
            return

        prompt = f"""
        Act as a world-class conversion copywriter. I need a JSON structure for a landing page for:
        Product: {product.name}
        Description: {product.description or 'No description'}
        Price: {campaign.currency} {product.selling_price}
        
        Context: Bangladeshi Market, Urgent, Emotional.
        
        Required JSON Structure (COPY THIS):
        {{
            "hero": {{ "headline": "...", "subheadline": "..." }},
            "features": [ {{ "title": "...", "text": "...", "icon": "⚡" }} ],
            "testimonials": [ {{ "name": "...", "text": "...", "rating": 5 }} ],
            "faq": [ {{ "question": "...", "answer": "..." }} ]
        }}
        """
        
        from django.http import HttpResponse # Import locally for safety
        return HttpResponse(prompt, content_type="text/plain")
        
    generate_external_prompt.short_description = "📋 Get External AI Prompt"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Check for Manual JSON paste
        if obj.manual_ai_prompt:
            try:
                import json
                from django.utils import timezone
                content = json.loads(obj.manual_ai_prompt)
                
                # Use existing logic to create variant (or new one)
                variant = obj.variants.create(
                    name=f"Manual AI Import {timezone.now().strftime('%H:%M')}",
                    weight=50
                )
                
                # Image Logic
                images = []
                if obj.product and obj.product.main_image_obj:
                    images.append(obj.product.main_image_obj.image.url)
                elif obj.product and obj.product.images.exists():
                     images.append(obj.product.images.first().image.url) 
                if not images:
                    images = ["https://placehold.co/600x400"]

                # 1. HERO
                variant.sections.create(
                    section_type='HERO_CAROUSEL',
                    order=0,
                    content={
                        "headline": content.get('hero', {}).get('headline', 'Offer'),
                        "subheadline": content.get('hero', {}).get('subheadline', ''),
                        "images": images
                    }
                )
                
                # 2. FEATURES
                if 'features' in content:
                    variant.sections.create(
                        section_type='FEATURES',
                        order=1,
                        content={"features": content['features']}
                    )

                # 3. TESTIMONIALS
                if 'testimonials' in content:
                    variant.sections.create(
                        section_type='TESTIMONIALS',
                        order=2,
                        content={"testimonials": content['testimonials']}
                    )

                # 4. FAQ
                if 'faq' in content:
                    variant.sections.create(
                        section_type='FAQ',
                        order=3,
                        content={"items": content['faq']}
                    )
                
                # Clear the field after processing
                obj.manual_ai_prompt = ""
                obj.save()
                
                self.message_user(request, "✅ Manual AI Content Imported Successfully!", level=messages.SUCCESS)
                
            except json.JSONDecodeError:
                self.message_user(request, "❌ Invalid JSON format in 'Manual AI Prompt'. Please check syntax.", level=messages.ERROR)
            except Exception as e:
                self.message_user(request, f"❌ Error processing JSON: {str(e)}", level=messages.ERROR)

    def generate_ai_content(self, request, queryset):
        success_count = 0
        error_messages = []
        
        for campaign in queryset:
            if not campaign.product:
                self.message_user(request, f"Skipped '{campaign.title}': No Product assigned.", level=messages.WARNING)
                continue
                
            content, error = generate_landing_copy(
                campaign.product.name, 
                campaign.product.description, 
                campaign.product.selling_price,
                campaign.currency
            )
            
            if error:
                error_messages.append(f"{campaign.title}: {error}")
                continue
            
            if content:
                # Create a new Variant populated with AI content
                variant = campaign.variants.create(
                    name="AI Generated Variant",
                    weight=0, # Manual activation needed
                    primary_color="#D4F759", # Default Lime
                )
                
                # Image Logic: Try main image, fall back to first gallery image, then placeholder
                images = []
                if campaign.product.main_image_obj:
                    images.append(campaign.product.main_image_obj.image.url)
                elif campaign.product.images.exists():
                    images.append(campaign.product.images.first().image.url)
                    
                if not images:
                    images = ["https://placehold.co/600x400?text=No+Image"]

                # 1. HERO
                variant.sections.create(
                    section_type='HERO_CAROUSEL',
                    order=0,
                    content={
                        "headline": content.get('hero', {}).get('headline', 'Special Offer'),
                        "subheadline": content.get('hero', {}).get('subheadline', ''),
                        "images": images
                    }
                )
                
                # 2. FEATURES
                if 'features' in content:
                    variant.sections.create(
                        section_type='FEATURES',
                        order=1,
                        content={"features": content['features']}
                    )
                    
                # 3. TESTIMONIALS
                if 'testimonials' in content:
                    variant.sections.create(
                        section_type='TESTIMONIALS',
                        order=2,
                        content={"testimonials": content['testimonials']}
                    )

                # 4. FAQ
                if 'faq' in content:
                    variant.sections.create(
                        section_type='FAQ',
                        order=3,
                        content={"items": content['faq']}
                    )
                
                success_count += 1
        
        if error_messages:
            self.message_user(request, "Errors: " + "; ".join(error_messages), level=messages.ERROR)

        if success_count:
            self.message_user(request, f"Successfully generated content for {success_count} campaigns.", level=messages.SUCCESS)
            
    generate_ai_content.short_description = "✨ Generate AI Content (Requires Gemin API)"
    
    def total_sessions(self, obj):
        return obj.sessions.count()
    
    def view_dashboard_link(self, obj):
        return format_html(
            '<a class="button" href="{}">📊 Live Dashboard</a>',
            f"/landing/analytics/{obj.slug}/"
        )
    view_dashboard_link.short_description = "Analytics"

@admin.register(CampaignVariant)
class CampaignVariantAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'name', 'weight', 'view_live_link')
    list_filter = ('campaign',)
    inlines = [LandingSectionInline]
    save_as = True
    
    def view_live_link(self, obj):
        return format_html(
            '<a class="button" target="_blank" href="{}">👁️ Preview Campaign</a>',
            f"/landing/{obj.campaign.slug}/?preview_variant={obj.id}"
        )
    view_live_link.short_description = "Preview"

@admin.register(VisitorSession)
class VisitorSessionAdmin(admin.ModelAdmin):
    list_display = ('session_uuid', 'campaign', 'variant', 'device_type', 'created_at')
    list_filter = ('campaign', 'device_type', 'country')
    search_fields = ('session_uuid', 'ip_address')
    readonly_fields = ('session_uuid', 'ip_address', 'user_agent', 'utm_source')

@admin.register(ConversionEvent)
class ConversionEventAdmin(admin.ModelAdmin):
    list_display = ('session', 'event_type', 'value', 'created_at')
    list_filter = ('event_type', 'created_at')