import time
from django.core.management.base import BaseCommand
from jeba_inventory.models import Product, Category
from jeba_seo.ai_engine import generate_category_and_tags

class Command(BaseCommand):
    help = 'AI Inventory Organizer: Suggests Categories and Tags'

    def handle(self, *args, **options):
        # 1. Get all valid categories to guide the AI
        all_categories = list(Category.objects.values_list('name', flat=True))
        if not all_categories:
            self.stdout.write(self.style.ERROR("No categories found in database! Create some first."))
            return

        # 2. Filter products that need organizing (e.g., no tags or no category)
        # You can remove the filter to re-process everything
        products = Product.objects.filter(tags__isnull=True).distinct()
        # For testing, let's just grab active ones
        products = Product.objects.filter(is_active=True)
        
        total = products.count()
        self.stdout.write(self.style.SUCCESS(f'Organizing {total} products using Categories: {all_categories}'))

        count = 0
        for product in products:
            count += 1
            self.stdout.write(f"[{count}/{total}] Organizing: {product.name}...")

            # 3. Call AI
            cat_suggestion, tags_list = generate_category_and_tags(
                product.name, 
                product.description or "", 
                all_categories
            )
            
            if cat_suggestion or tags_list:
                # 4. Save to Staging Fields
                if cat_suggestion:
                    product.ai_suggested_category = cat_suggestion
                
                if tags_list:
                    # Store as comma-separated string
                    product.ai_suggested_tags = ", ".join(tags_list)
                
                product.save()
                self.stdout.write(self.style.SUCCESS(f" > Suggested: {cat_suggestion} | Tags: {len(tags_list)}"))
            else:
                self.stdout.write(self.style.ERROR(" > Failed"))

            # Rate Limit (Safety)
            time.sleep(2)