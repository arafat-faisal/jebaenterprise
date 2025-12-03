"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings               
from django.conf.urls.static import static

# --- MODULAR ERROR HANDLERS ---
# We now point to the 'jeba_core' app where we moved these views
handler404 = 'jeba_core.views.custom_404'
handler500 = 'jeba_core.views.custom_500'

urlpatterns = [
    # --- ADD THIS LINE ---
    path('i18n/', include('django.conf.urls.i18n')),
    # ---------------------
    path('admin/', admin.site.urls),
    
    # Replaced standard auth urls with our custom modular app urls
    path("accounts/", include("jeba_accounts.urls")),
    
    # The main router remains in products.urls
    path("", include("products.urls")),
    path('blog/', include('jeba_blog.urls')),
    path('sales/', include('jeba_sales.urls')),
    # --- NEW: Plug in the AI SEO App ---
    path('seo/', include('jeba_seo.urls')),  # <--- ADD THIS LINE
    # -----------------------------------
    path("landing/", include("jeba_landing.urls")),
    path('analytics/', include('jeba_analytics.urls')), # <--- ADD THIS
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)