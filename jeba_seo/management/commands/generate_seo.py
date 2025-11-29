import time
from django.core.management.base import BaseCommand
from jeba_inventory.models import Product
from jeba_seo.ai_engine import generate_product_content

class Command(BaseCommand):
    help = 'Generates AI Content (JSON/HTML Mode)'

    def handle(self, *args, **options):
        products = Product.objects.filter(is_seo_optimized=False)
        total = products.count()
        self.stdout.write(self.style.SUCCESS(f'Starting AI Architect for {total} products...'))

        count = 0
        for product in products:
            count += 1
            self.stdout.write(f"[{count}/{total}] Analyzing: {product.name}...")
            
            # Get Image
            img_path = None
            if product.main_image_obj and product.main_image_obj.image:
                img_path = product.main_image_obj.image.path
            
            # Call AI (New JSON Return)
            data = generate_product_content(
                product.name, 
                product.description, 
                product.category.name if product.category else "General", 
                img_path
            )
            
            if data:
                # Update Fields from Dictionary
                product.ai_suggested_name = data.get('display_name')
                product.ai_suggested_description = data.get('description') # This is now HTML
                product.meta_title_ai = data.get('meta_title')
                product.meta_description_ai = data.get('meta_description')
                
                product.is_seo_optimized = True
                product.save()
                self.stdout.write(self.style.SUCCESS(f" > Success!"))
            else:
                self.stdout.write(self.style.ERROR(f" > Failed"))

            time.sleep(4)