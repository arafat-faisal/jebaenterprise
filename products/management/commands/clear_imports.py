from django.core.management.base import BaseCommand
from products.models import Product, Category

class Command(BaseCommand):
    help = 'Deletes all products in the "Imported New" category'

    def handle(self, *args, **kwargs):
        target_category = "Imported New"
        
        # check if category exists
        try:
            category = Category.objects.get(name=target_category)
        except Category.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'Category "{target_category}" not found. Nothing to delete.'))
            return

        # Count before delete
        count = Product.objects.filter(category=category).count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No products found in that category.'))
            return

        self.stdout.write(f'Found {count} products in "{target_category}". Deleting...')
        
        # Delete (Cascade will remove ProductImages automatically)
        Product.objects.filter(category=category).delete()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} products.'))