"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings               
from django.conf.urls.static import static

# --- Define Custom Error Handlers ---
# These point to the views we will create in the next step
handler404 = 'products.views.custom_404'
handler500 = 'products.views.custom_500'

urlpatterns = [
    path('admin/', admin.site.urls),
    # --- ADD THIS LINE ---
    # This tells Django: "For any URL that isn't 'admin/',
    # go look for a new urls.py file inside the 'products' app."
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("products.urls")),
]
# --- ADD THIS LINE AT THE BOTTOM ---
# This serves your uploaded images in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)