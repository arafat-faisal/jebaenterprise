from django.core.management.base import BaseCommand
from jeba_landing.models import Campaign, CampaignVariant
try:
    from jeba_inventory.models import Product
except ImportError:
    Product = None

class Command(BaseCommand):
    help = 'Creates a fully functional demo landing page.'

    def handle(self, *args, **options):
        # 1. Get or Create a Product
        product = Product.objects.first()
        if not product:
            self.stdout.write(self.style.ERROR("No products found! Create a product in inventory first."))
            return

        # 2. Create Campaign
        campaign, created = Campaign.objects.get_or_create(
            slug='demo-offer',
            defaults={
                'title': f"Mega Deal: {product.name}",
                'product': product,
                'is_active': True,
                'currency': 'BDT'
            }
        )
        
        if not created:
            self.stdout.write(self.style.WARNING("Demo campaign already exists. Resetting variants..."))
            campaign.variants.all().delete()
            
        # 3. Create Variant
        variant = CampaignVariant.objects.create(
            campaign=campaign,
            name="High Conv. V1",
            weight=100,
            primary_color="#D4F759", # Neon Lime
            enable_social_proof=True,
            enable_fomo_timer=True
        )
        
        # 4. Add Sections
        # Hero
        variant.sections.create(
            section_type='HERO_CAROUSEL',
            order=0,
            content={
                "headline": "Stop Wasting Money on Quality 🔥",
                "subheadline": f"Get the authentic {product.name} at an unbeatable price. Limited stock available for Dhaka delivery.",
                "images": [product.main_image_obj.image.url] if product.main_image_obj else ["https://placehold.co/600x400"]
            }
        )
        
        # Features
        variant.sections.create(
            section_type='FEATURES',
            order=1,
            content={
                "features": [
                    {"title": "Genuine Product", "text": "100% Authentic sourced directly.", "icon": "💎"},
                    {"title": "Fast Delivery", "text": "Get it within 24 hours in Dhaka.", "icon": "🚀"},
                    {"title": "Money Back", "text": "7 Days return policy if not satisfied.", "icon": "🛡️"}
                ]
            }
        )

        # Testimonials
        variant.sections.create(
            section_type='TESTIMONIALS',
            order=2,
            content={
                "testimonials": [
                    {"name": "Rahim U.", "text": "Amazing quality, received it in 2 days!", "rating": 5},
                    {"name": "Sumaiya K.", "text": "Best price in the market. Highly recommended.", "rating": 5},
                    {"name": "Tanvir A.", "text": "Very satisfied with the customer service.", "rating": 5}
                ]
            }
        )

        # FAQ
        variant.sections.create(
            section_type='FAQ',
            order=3,
            content={
                "items": [
                    {"question": "Is delivery free?", "answer": "Yes, we offer free delivery inside Dhaka city."},
                    {"question": "Can I check before paying?", "answer": "Absolutely! We assume open box delivery."},
                    {"question": "What is the return policy?", "answer": "You can return specifically if there is any damage found during delivery."}
                ]
            }
        )
        
        self.stdout.write(self.style.SUCCESS(f"Successfully created Demo Campaign!\nURL: /landing/{campaign.slug}/"))
