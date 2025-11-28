class AnalyticsMiddleware:
    """
    Captures marketing attribution parameters (UTMs) from the URL
    and persists them in the user's session.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of params we care about
        utm_params = ['utm_source', 'utm_medium', 'utm_campaign']
        
        # Check if any UTM params exist in the current URL query string
        if any(param in request.GET for param in utm_params):
            utm_data = {}
            for param in utm_params:
                value = request.GET.get(param)
                if value:
                    utm_data[param] = value[:50] # Truncate to fit DB limits
            
            # Save to session (persistence)
            # This ensures that even if they click 5 links deep, we know where they came from.
            if utm_data:
                request.session['utm_data'] = utm_data
                request.session.modified = True

        response = self.get_response(request)
        return response