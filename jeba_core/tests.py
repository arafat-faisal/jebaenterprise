from django.test import TestCase, Client
from jeba_core.models import SiteSettings

class CoreSettingsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.settings = SiteSettings.load()

    def test_maintenance_mode(self):
        """Feature: Maintenance Mode"""
        # Turn ON maintenance
        self.settings.maintenance_mode = True
        self.settings.save()

        response = self.client.get('/')
        self.assertContains(response, "We'll Be Back Soon") # Checks for text in maintenance.html

        # Admin should still be accessible (returns login page or admin page, not maintenance)
        response = self.client.get('/admin/login/')
        self.assertNotContains(response, "We'll Be Back Soon")