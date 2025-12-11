from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
import os

# Import your models that have images
from jeba_inventory.models import ProductImage, ProductVariation

class Command(BaseCommand):
    help = 'Updates database records to point to .webp images if they exist'

    def handle(self, *args, **options):
        self.stdout.write("🔄 Starting Database Switchover to WebP...")
        
        updated_count = 0
        
        # 1. Update Product Images
        self.stdout.write("   Checking ProductGallery Images...")
        for obj in ProductImage.objects.all():
            if self.process_field(obj, 'image'):
                updated_count += 1
            if self.process_field(obj, 'transparent_image'):
                updated_count += 1

        # 2. Update Variations
        self.stdout.write("   Checking Variation Images...")
        for obj in ProductVariation.objects.all():
            if self.process_field(obj, 'image'):
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"✨ DONE! Updated database records for {updated_count} images."))

    def process_field(self, obj, field_name):
        """
        Checks if a WebP version exists for the given field.
        If yes, updates the DB record.
        """
        file_field = getattr(obj, field_name)
        
        # Skip if empty or already WebP
        if not file_field or file_field.name.lower().endswith('.webp'):
            return False

        # Construct current full path and target WebP path
        current_path = file_field.path
        base_name, _ = os.path.splitext(current_path)
        webp_path = base_name + ".webp"
        
        # Check if the WebP file actually exists on disk
        if os.path.exists(webp_path):
            # Calculate new relative name for DB (e.g., 'products/gallery/img.webp')
            current_name = file_field.name
            base_rel_name, _ = os.path.splitext(current_name)
            new_name = base_rel_name + ".webp"
            
            # Update the field name directly
            # We use a localized save to avoid triggering signals/re-processing if possible
            setattr(obj, field_name, new_name)
            obj.save(update_fields=[field_name])
            
            self.stdout.write(f"      ✔ Switched {current_name} -> .webp")
            return True
        
        return False