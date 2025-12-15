from django.test import TestCase, Client
from django.urls import reverse
from .models import Campaign, CampaignVariant, VisitorSession, ConversionEvent

class CampaignDispatcherTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.campaign = Campaign.objects.create(
            title="Eid Sale", 
            slug="eid-sale", 
            is_active=True
        )
        self.variant_a = CampaignVariant.objects.create(
            campaign=self.campaign,
            name="Variant A",
            weight=100
        )
        # Create a section to ensure rendering works
        self.variant_a.sections.create(
            section_type='HERO_CAROUSEL', 
            content={'headline': 'Test Hero'}
        )

    def test_campaign_redirects_assigns_variant(self):
        """Test that a new visitor gets assigned a variant and a session cookie."""
        response = self.client.get(reverse('campaign_detail', args=['eid-sale']))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Hero')
        
        # Check Cookie
        self.assertIn('jeba_lid', response.cookies)
        
        # Check DB
        session_id = response.cookies['jeba_lid'].value
        session = VisitorSession.objects.get(session_uuid=session_id)
        self.assertEqual(session.campaign, self.campaign)
        self.assertEqual(session.variant, self.variant_a)
        
    def test_tracking_api(self):
        """Test the pixel tracking endpoint."""
        # Create a session first
        session = VisitorSession.objects.create(campaign=self.campaign, variant=self.variant_a)
        
        url = reverse('landing_track_event')
        data = {
            'session_id': str(session.session_uuid),
            'event_type': 'CLICK_CTA',
            'metadata': {'btn': 'Buy Now'}
        }
        
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        # Verify
        event = ConversionEvent.objects.first()
        self.assertEqual(event.event_type, 'CLICK_CTA')
