import json
from django.conf import settings

class AnalyticsService:
    """
    Central intelligence engine for extracting user context from requests.
    """

    @staticmethod
    def get_client_ip(request):
        """Smart extraction of IP address handling proxies/Cloudflare."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def get_device_info(request):
        """
        Parses User-Agent to determine device type.
        For production, consider using 'django-user_agents' for deeper parsing.
        """
        ua_string = request.META.get('HTTP_USER_AGENT', '').lower()
        
        device_type = 'desktop'
        
        # 1. Tablets (iPad often doesn't say "mobile")
        if 'tablet' in ua_string or 'ipad' in ua_string:
            device_type = 'tablet'
        # 2. Mobile (Check for 'mobile' OR specific phone identifiers)
        elif 'mobile' in ua_string or 'iphone' in ua_string or 'android' in ua_string:
            device_type = 'mobile'
            
        # Basic OS detection
        os = 'unknown'
        if 'android' in ua_string: os = 'android'
        elif 'iphone' in ua_string or 'ipad' in ua_string: os = 'ios'
        elif 'windows' in ua_string: os = 'windows'
        elif 'macintosh' in ua_string: os = 'mac'
        elif 'linux' in ua_string: os = 'linux'

        return {
            'raw_ua': ua_string,
            'type': device_type,
            'os': os,
            'browser_width': None, # Requires JS to capture
        }

    @staticmethod
    def get_traffic_source(request):
        """Captures UTM parameters and Referrer for marketing attribution."""
        return {
            'referrer': request.META.get('HTTP_REFERER', ''),
            'utm_source': request.GET.get('utm_source', ''),
            'utm_medium': request.GET.get('utm_medium', ''),
            'utm_campaign': request.GET.get('utm_campaign', ''),
            'utm_content': request.GET.get('utm_content', ''),
        }

    @classmethod
    def get_context(cls, request):
        """
        Master method to aggregate all context data.
        Call this from your views to populate the 'metadata' field.
        """
        if not request:
            return {}

        ip = cls.get_client_ip(request)
        
        # Location Logic (Placeholder)
        # In production, you would use GeoIP2 database here using the IP
        location_data = {
            'ip': ip,
            'city': None,     # Requires GeoIP
            'country': None,  # Requires GeoIP
        }

        # Safe Session Key Access (Handle cases where middleware is missing)
        session_key = 'anonymous'
        if hasattr(request, 'session') and request.session.session_key:
            session_key = request.session.session_key

        return {
            'location': location_data,
            'device': cls.get_device_info(request),
            'marketing': cls.get_traffic_source(request),
            'session_key': session_key
        }