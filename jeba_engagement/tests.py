from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from jeba_inventory.models import Product
from jeba_engagement.models import Review, Wishlist

class EngagementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='reviewer', password='password123')
        self.product = Product.objects.create(name="Review Item", selling_price=100)
        self.client.login(username='reviewer', password='password123')

    def test_add_review(self):
        """Feature: Submit Review"""
        url = reverse('add_review', args=[self.product.id])
        data = {'rating': 5, 'comment': 'Great product!'}
        
        response = self.client.post(url, data)
        
        # Check DB
        self.assertTrue(Review.objects.filter(product=self.product, rating=5).exists())

    def test_wishlist_toggle(self):
        """Feature: Wishlist Add/Remove"""
        url = reverse('toggle_wishlist', args=[self.product.id])
        
        # 1. Add to Wishlist
        self.client.get(url)
        self.assertTrue(Wishlist.objects.filter(user=self.user, product=self.product).exists())
        
        # 2. Remove from Wishlist (Toggle)
        self.client.get(url)
        self.assertFalse(Wishlist.objects.filter(user=self.user, product=self.product).exists())