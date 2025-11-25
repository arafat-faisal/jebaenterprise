from django.test import TestCase, Client
from django.urls import reverse
from jeba_inventory.models import Product, Category

class CatalogFeatureTest(TestCase):
    def setUp(self):
        self.client = Client()
        # FIX: Use get_or_create to prevent Duplicate Key errors
        self.cat_elec, _ = Category.objects.get_or_create(name="Electronics")
        self.cat_fashion, _ = Category.objects.get_or_create(name="Fashion")
        
        # Clear products to ensure a clean slate for each test
        Product.objects.all().delete()
        
        self.p1 = Product.objects.create(
            name="Phone", 
            category=self.cat_elec, 
            selling_price=10000, 
            stock_quantity=10,
            is_featured=True
        )
        self.p2 = Product.objects.create(
            name="Shirt", 
            category=self.cat_fashion, 
            selling_price=500, 
            stock_quantity=0
        )

    def test_homepage_loads(self):
        """Feature: Homepage Hero"""
        response = self.client.get(reverse('pricing_sheet'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Phone")

    def test_category_filter(self):
        """Feature: Filter by Category"""
        url = reverse('product_catalog')
        response = self.client.get(url, {'category': self.cat_elec.id})
        self.assertContains(response, "Phone")
        self.assertNotContains(response, "Shirt")

    def test_price_sorting(self):
        """Feature: Sort by Price"""
        url = reverse('product_catalog')
        # Low to High
        response = self.client.get(url, {'sort': 'price-low'})
        products = list(response.context['products'])
        self.assertEqual(products[0], self.p2) # Shirt (500) should be first

    def test_stock_badge_logic(self):
        """Feature: Low Stock Warning"""
        # p1 has 10 stock -> "In Stock"
        response = self.client.get(reverse('product_detail', args=[self.p1.id]))
        self.assertContains(response, "In Stock")

        # p2 has 0 stock -> "Out of Stock"
        response = self.client.get(reverse('product_detail', args=[self.p2.id]))
        self.assertContains(response, "Out of Stock")

    def test_search_functionality(self):
        """Feature: Text Search"""
        response = self.client.get(reverse('search'), {'q': 'Phone'})
        self.assertEqual(len(response.context['products']), 1)