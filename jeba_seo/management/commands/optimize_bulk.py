import time
from django.core.management.base import BaseCommand
from jeba_inventory.models import Product, Category, Tag
from jeba_seo.ai_engine import generate_bulk_analysis

class Command(BaseCommand):
    help = 'Optimizes products in BATCHES (Faster & Cheaper)'

    def handle(self, *args, **options):
        # 1. Configuration
        BATCH_SIZE = 10  # How many products to send at once
        
        # Get Categories for context
        all_categories = list(Category.objects.values_list('name', flat=True))
        
        # Filter products that need work (e.g., active ones)
        # You can adjust this filter (e.g., is_seo_optimized=False)
        products_qs = Product.objects.filter(is_active=True).order_by('id')
        total_products = products_qs.count()
        
        self.stdout.write(self.style.SUCCESS(f"Starting Bulk Optimization for {total_products} products..."))

        # 2. Process in Chunks
        for offset in range(0, total_products, BATCH_SIZE):
            batch_products = products_qs[offset:offset+BATCH_SIZE]
            
            # Prepare data for the Engine
            data_payload = []
            for p in batch_products:
                data_payload.append({
                    'id': p.id,
                    'name': p.name,
                    'description': p.description or ""
                })
            
            self.stdout.write(f"Processing Batch {offset}-{offset+len(batch_products)}...")
            
            # 3. Call the Bulk AI Engine
            results = generate_bulk_analysis(data_payload, all_categories)
            
            if results:
                # 4. Save Results
                success_count = 0
                for p in batch_products:
                    if p.id in results:
                        data = results[p.id]
                        
                        # Update SEO
                        p.meta_title_ai = data.get('title')
                        p.meta_description_ai = data.get('description')
                        p.is_seo_optimized = True
                        
                        # Update Organizer Fields
                        p.ai_suggested_category = data.get('category')
                        p.ai_suggested_tags = data.get('tags')
                        
                        p.save()
                        success_count += 1
                
                self.stdout.write(self.style.SUCCESS(f" > Successfully updated {success_count}/{len(batch_products)} in this batch."))
            else:
                self.stdout.write(self.style.ERROR(" > Batch failed (AI Error)."))

            # Sleep briefly to be polite to the API, even though we made fewer calls
            time.sleep(2)

        self.stdout.write(self.style.SUCCESS("Bulk Optimization Complete!"))