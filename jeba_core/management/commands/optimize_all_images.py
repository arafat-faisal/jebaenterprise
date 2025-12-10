from django.core.management.base import BaseCommand
from jeba_inventory.models import ProductImage, ProductVariation
from jeba_landing.models import LandingSection
from jeba_blog.models import BlogPost
from jeba_core.image_optimizer import optimize_image, generate_lqip

class Command(BaseCommand):
    help = '🚀 Convert all images to WebP and generate Blur-Up Placeholders'

    def handle(self, *args, **options):
        self.stdout.write("🔥 Starting Level 2 Optimization (WebP + Blur-Up)...")

        # 1. Product Images
        for item in ProductImage.objects.all():
            if item.image:
                self.stdout.write(f"Processing ProductImage {item.id}...")
                # Optimize
                if not item.image.name.endswith('.webp'):
                    item.image = optimize_image(item.image, 1200)
                # Generate Placeholder
                item.placeholder = generate_lqip(item.image)
                item.save()

        # 2. Product Variations
        for item in ProductVariation.objects.all():
            if item.image:
                self.stdout.write(f"Processing Variation {item.id}...")
                if not item.image.name.endswith('.webp'):
                    item.image = optimize_image(item.image, 800)
                item.image_placeholder = generate_lqip(item.image)
                item.save()

        # 3. Blog Posts
        for item in BlogPost.objects.all():
            if item.featured_image:
                self.stdout.write(f"Processing Blog {item.id}...")
                if not item.featured_image.name.endswith('.webp'):
                    item.featured_image = optimize_image(item.featured_image, 1200)
                item.featured_image_placeholder = generate_lqip(item.featured_image)
                item.save()

        # 4. Landing Sections
        for item in LandingSection.objects.all():
            self.stdout.write(f"Processing Section {item.id}...")
            # We trigger the save() method which has the logic built-in
            # But we force a "dirty" check or just save to trigger it
            item.save() 

        self.stdout.write(self.style.SUCCESS("✅ ALL IMAGES UPGRADED TO PREMIUM UX!"))