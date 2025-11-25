import json
import os
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
        """
        ua_string = request.META.get('HTTP_USER_AGENT', '').lower()
        
        device_type = 'desktop'
        
        # 1. Tablets
        if 'tablet' in ua_string or 'ipad' in ua_string:
            device_type = 'tablet'
        # 2. Mobile
        elif 'mobile' in ua_string or 'iphone' in ua_string or 'android' in ua_string:
            device_type = 'mobile'
            
        # Basic OS detection
        os_name = 'unknown'
        if 'android' in ua_string: os_name = 'android'
        elif 'iphone' in ua_string or 'ipad' in ua_string: os_name = 'ios'
        elif 'windows' in ua_string: os_name = 'windows'
        elif 'macintosh' in ua_string: os_name = 'mac'
        elif 'linux' in ua_string: os_name = 'linux'

        return {
            'raw_ua': ua_string,
            'type': device_type,
            'os': os_name,
            'browser_width': None, 
        }

    @staticmethod
    def get_traffic_source(request):
        """Captures UTM parameters and Referrer."""
        return {
            'referrer': request.META.get('HTTP_REFERER', ''),
            'utm_source': request.GET.get('utm_source', ''),
            'utm_medium': request.GET.get('utm_medium', ''),
            'utm_campaign': request.GET.get('utm_campaign', ''),
            'utm_content': request.GET.get('utm_content', ''),
        }

    @classmethod
    def get_location_from_ip(cls, ip):
        """
        Resolves IP to Location using local GeoIP2 Database.
        """
        # Skip localhost
        if ip in ['127.0.0.1', '::1']:
            return {'city': 'Localhost', 'country': 'Localhost'}

        try:
            import geoip2.database
            
            # Look for DB in 'geoip' folder in project root
            db_path = os.path.join(settings.BASE_DIR, 'geoip', 'GeoLite2-City.mmdb')
            
            if not os.path.exists(db_path):
                return {'city': None, 'country': None, 'error': 'DB missing'}

            with geoip2.database.Reader(db_path) as reader:
                response = reader.city(ip)
                return {
                    'city': response.city.name,
                    'country': response.country.name,
                    'iso_code': response.country.iso_code
                }
        except ImportError:
            return {'city': None, 'country': None, 'error': 'Install geoip2'}
        except Exception:
            return {'city': None, 'country': None}

    @classmethod
    def get_context(cls, request):
        """
        Master method to aggregate all context data.
        """
        if not request:
            return {}

        ip = cls.get_client_ip(request)
        
        # if ip == '127.0.0.1':
        #     ip = '103.72.212.247'  # Default IP for local testing

        # Enhanced Location Logic
        location_data = {'ip': ip}
        location_data.update(cls.get_location_from_ip(ip))

        # Safe Session Key
        session_key = 'anonymous'
        if hasattr(request, 'session') and request.session.session_key:
            session_key = request.session.session_key

        return {
            'location': location_data,
            'device': cls.get_device_info(request),
            'marketing': cls.get_traffic_source(request),
            'session_key': session_key
        }