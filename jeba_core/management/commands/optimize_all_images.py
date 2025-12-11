from django.core.management.base import BaseCommand
from django.conf import settings
from PIL import Image
import os
import shutil

class Command(BaseCommand):
    help = 'Aggressively optimizes product images (WebP conversion + Resizing)'

    def handle(self, *args, **options):
        # Configuration
        MAX_WIDTH = 1200  # Max width in pixels
        QUALITY = 80      # Quality percentage
        
        media_root = settings.MEDIA_ROOT
        
        self.stdout.write(f"🚀 Starting Optimization Engine...")
        self.stdout.write(f"   - Target Width: {MAX_WIDTH}px")
        self.stdout.write(f"   - Target Quality: {QUALITY}%")
        self.stdout.write(f"   - Format: WebP")

        optimized_count = 0
        saved_space = 0

        # Walk through all files in MEDIA_ROOT
        for root, dirs, files in os.walk(media_root):
            for filename in files:
                file_path = os.path.join(root, filename)
                
                # Check extension
                if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                    
                # Skip if it's already a .webp (we might have converted it manually)
                if filename.lower().endswith('.webp'):
                    continue

                try:
                    # Open Image
                    with Image.open(file_path) as img:
                        original_size = os.path.getsize(file_path)
                        
                        # Check if resizing is needed
                        width, height = img.size
                        if width > MAX_WIDTH:
                            ratio = MAX_WIDTH / width
                            new_height = int(height * ratio)
                            img = img.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
                        
                        # Construct new filename (replace extension with .webp)
                        file_root, _ = os.path.splitext(file_path)
                        new_file_path = file_root + ".webp"
                        
                        # Save as WebP
                        # If RGBA (PNG), keep transparency. If RGB (JPG), straightforward.
                        if img.mode in ("RGBA", "P"):
                            img.save(new_file_path, "WEBP", quality=QUALITY, optimize=True)
                        else:
                            img = img.convert("RGB")
                            img.save(new_file_path, "WEBP", quality=QUALITY, optimize=True)
                        
                        # Calculate Savings
                        new_size = os.path.getsize(new_file_path)
                        savings = original_size - new_size
                        
                        if savings > 0:
                            saved_space += savings
                            optimized_count += 1
                            self.stdout.write(self.style.SUCCESS(f"✔ Optimized: {filename} ({savings/1024:.1f} KB saved)"))
                            
                            # OPTIONAL: Delete original file to save server space?
                            # For safety, I am NOT deleting originals automatically yet.
                            # os.remove(file_path) 
                        else:
                            # If WebP is bigger (rare), keep original? 
                            # Usually we prefer WebP for consistency, but for now let's keep both.
                            pass

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Failed: {filename} - {str(e)}"))

        total_mb = saved_space / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(f"✨ DONE! Optimized {optimized_count} images. Total Saved: {total_mb:.2f} MB"))