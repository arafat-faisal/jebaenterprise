from django.shortcuts import render

def about_us(request):
    return render(request, 'jeba_core/about.html')

def contact_us(request):
    return render(request, 'jeba_core/contact.html')

def custom_404(request, exception):
    return render(request, 'jeba_core/404.html', status=404)

def custom_500(request):
    return render(request, 'jeba_core/500.html', status=500)

def privacy_policy(request):
    """
    Renders the Privacy Policy page required by Facebook.
    """
    return render(request, 'jeba_core/privacy_policy.html')