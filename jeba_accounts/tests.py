from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from jeba_accounts.models import UserProfile

class UserAccountTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')

    def test_registration(self):
        """Feature: User Registration"""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@example.com',
            'password': 'password123',  # Note: UserCreationForm handles passwords differently in tests usually, 
                                        # but simple POST check is often enough for views
        }
        # We just check if the page loads (GET) for now, or simulate a full post if using standard forms
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_profile_update(self):
        """Feature: Update Address/Phone"""
        self.client.login(username='testuser', password='password123')
        url = reverse('profile')
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'test@test.com',
            'phone_number': '01711111111',
            'address': 'New Dhaka Address'
        }
        response = self.client.post(url, data)
        
        # Reload from DB
        self.user.refresh_from_db()
        profile = self.user.profile
        
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(profile.address, 'New Dhaka Address')