from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SaleItem

@receiver(post_save, sender=SaleItem)
def deduct_stock_on_sale_item_creation(sender, instance, created, **kwargs):
    """
    Deducts stock quantity from Product and ProductVariation after a SaleItem is created.
    Uses the post_save signal for decoupled inventory management.
    """
    # Only run the logic when the instance is first created
    if created:
        product = instance.product
        quantity = instance.quantity

        # Deduct from Product (update_fields prevents triggering infinite save loops if product also had signals)
        product.stock_quantity -= quantity
        product.save(update_fields=['stock_quantity'])

        # Deduct from Variation, if applicable
        if instance.variation:
            variation = instance.variation
            variation.stock_quantity -= quantity
            variation.save(update_fields=['stock_quantity'])