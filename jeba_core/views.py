from django.shortcuts import render

def about_us(request):
    return render(request, 'jeba_core/about.html')

def contact_us(request):
    return render(request, 'jeba_core/contact.html')

def custom_404(request, exception):
    return render(request, 'jeba_core/404.html', status=404)

def custom_500(request):
    return render(request, 'jeba_core/500.html', status=500)