from django.shortcuts import render

def about_us(request):
    return render(request, 'products/about.html')

def contact_us(request):
    return render(request, 'products/contact.html')

def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)