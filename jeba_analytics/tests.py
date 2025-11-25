from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware # <--- Added Import
from jeba_inventory.models import Product, Category
from jeba_analytics.models import ProductEvent, SearchEvent
from jeba_analytics.analytics_service import AnalyticsService
import json

class AnalyticsServiceTest(TestCase):
    """
    Level 1: Unit Test the Logic (The 'Brain')
    """
    def setUp(self):
        self.factory = RequestFactory()

    def test_context_extraction(self):
        """Does it correctly capture iPhone, IP, and Marketing tags?"""
        
        # 1. Simulate a Request with specific headers
        request = self.factory.get(
            '/?utm_source=facebook&utm_campaign=summer_sale',
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)',
            HTTP_X_FORWARDED_FOR='203.0.113.55', # Fake IP
            HTTP_REFERER='https://google.com'
        )
        
        # --- FIX: Manually add Session support for RequestFactory ---
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        # -----------------------------------------------------------
        
        # 2. Run the Service
        context = AnalyticsService.get_context(request)
        
        # 3. Verify Data
        # IP Check
        self.assertEqual(context['location']['ip'], '203.0.113.55')
        
        # Device Check
        self.assertEqual(context['device']['type'], 'mobile')
        self.assertEqual(context['device']['os'], 'ios')
        
        # Marketing Check
        self.assertEqual(context['marketing']['utm_source'], 'facebook')
        self.assertEqual(context['marketing']['utm_campaign'], 'summer_sale')
        self.assertEqual(context['marketing']['referrer'], 'https://google.com')


class AnalyticsIntegrationTest(TestCase):
    """
    Level 2: Integration Test (The 'Wiring')
    Simulates real users browsing the site using Client (which handles sessions automatically).
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        
        # Setup Product
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            name="Test Phone", 
            category=self.category, 
            selling_price=10000,
            stock_quantity=10
        )

    def test_product_view_tracking(self):
        """Feature: Visiting a product page logs a VIEW event with metadata"""
        
        # Visit Page as an iPhone user
        url = reverse('product_detail', args=[self.product.id])
        response = self.client.get(
            url, 
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 14...)'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check DB
        event = ProductEvent.objects.last()
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, 'VIEW')
        self.assertEqual(event.product, self.product)
        # Did we save the device info?
        self.assertEqual(event.metadata['device']['os'], 'ios')

    def test_cart_tracking(self):
        """Feature: Adding to cart logs a CART event"""
        url = reverse('add_to_cart', args=[self.product.id])
        self.client.post(url, {'quantity': 1, 'action': 'add'})
        
        event = ProductEvent.objects.filter(event_type='CART').last()
        self.assertIsNotNone(event)
        self.assertEqual(event.product.name, "Test Phone")

    def test_js_interaction_tracking(self):
        """Feature: JS Tracking Endpoint (WhatsApp/Messenger clicks)"""
        url = reverse('track_interaction')
        
        payload = {
            'product_id': self.product.id,
            'event_type': 'CONTACT',
            'extra': {'channel': 'WhatsApp'}
        }
        
        # Simulate JS Fetch call
        response = self.client.post(
            url, 
            data=payload, 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'recorded')
        
        # Check DB
        event = ProductEvent.objects.last()
        self.assertEqual(event.event_type, 'CONTACT')
        self.assertEqual(event.metadata['channel'], 'WhatsApp')

    def test_search_tracking(self):
        """Feature: Search logging"""
        url = reverse('search')
        self.client.get(url, {'q': 'Phone'})
        
        event = SearchEvent.objects.last()
        self.assertEqual(event.query, 'Phone')
        self.assertIn('device', event.metadata)