from django.test import TestCase, Client
from django.urls import reverse
from jeba_inventory.models import Product
from jeba_sales.models import Sale
from jeba_core.models import SiteSettings

class CheckoutProcessTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Use get_or_create for settings to avoid conflicts
        SiteSettings.objects.get_or_create(delivery_charge_inside=60, delivery_charge_outside=120)
        
        self.product = Product.objects.create(
            name="Premium Watch",
            selling_price=5000,
            stock_quantity=10
        )

    def test_add_to_cart(self):
        """Feature: Add to Cart"""
        url = reverse('add_to_cart', args=[self.product.id])
        self.client.post(url, {'quantity': 2, 'action': 'add'})
        
        session = self.client.session
        self.assertIn(str(self.product.id), session['cart'])
        self.assertEqual(session['cart'][str(self.product.id)]['quantity'], 2)

    def test_checkout_stock_deduction(self):
        """Feature: Checkout & Stock Logic"""
        # 1. Setup Cart
        cart = {
            str(self.product.id): {
                'name': self.product.name,
                'price': float(self.product.selling_price),
                'quantity': 2,
                'product_id': self.product.id,
                'variation_id': None
            }
        }
        session = self.client.session
        session['cart'] = cart
        session.save()

        # 2. Perform Checkout
        url = reverse('checkout')
        data = {
            'customer_name': 'Test User',
            'phone_number': '01700000000',
            'shipping_address': 'Dhaka',
            'delivery_area': 'INSIDE',
            'payment_method': 'COD'
        }
        response = self.client.post(url, data)

        # 3. Verify Success
        self.assertRedirects(response, reverse('order_success'))

        # 4. Verify DB
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8) # 10 - 2 = 8

class AdvancedCheckoutTest(TestCase):
    def setUp(self):
        self.client = Client()
        SiteSettings.objects.get_or_create(delivery_charge_inside=60, delivery_charge_outside=120)
        
        self.product = Product.objects.create(name="Item", selling_price=1000, stock_quantity=10)
        
        # Setup Cart Session
        session = self.client.session
        session['cart'] = {
            str(self.product.id): {
                'name': 'Item', 'price': 1000, 'quantity': 1, 
                'product_id': self.product.id, 'variation_id': None
            }
        }
        session.save()

    def test_delivery_charge_outside(self):
        """Feature: Delivery Charge Logic (Outside Dhaka)"""
        url = reverse('checkout')
        data = {
            'customer_name': 'User', 
            'phone_number': '01700000000', 
            'shipping_address': 'Ctg',
            'delivery_area': 'OUTSIDE',
            'payment_method': 'COD'
        }
        self.client.post(url, data)
        
        sale = Sale.objects.last()
        self.assertEqual(sale.delivery_charge, 120)
        self.assertEqual(sale.total_amount, 1120)

    def test_bkash_validation(self):
        """Feature: bKash Transaction ID Requirement"""
        url = reverse('checkout')
        data = {
            'customer_name': 'User', 
            'phone_number': '01700000000', 
            'shipping_address': 'Dhaka',
            'delivery_area': 'INSIDE',
            'payment_method': 'BKASH',
            'transaction_id': '' # ERROR: Empty TrxID
        }
        response = self.client.post(url, data)
        
        # Should NOT redirect (200 OK implies it stayed on page to show errors)
        self.assertEqual(response.status_code, 200) 
        
        # FIX: Manually check the form errors in context
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('transaction_id', form.errors)
        self.assertEqual(form.errors['transaction_id'][0], "Transaction ID is required for bKash payment.")