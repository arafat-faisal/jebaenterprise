"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings               
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap # <--- Import this
from jeba_seo.sitemaps import ProductSitemap, CategorySitemap, BlogPostSitemap, StaticViewSitemap # <--- Import sitemaps
from jeba_seo.views import robots_txt # <--- Import robots view


# Define the dictionary of sitemaps
sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
    'blog': BlogPostSitemap,
    'static': StaticViewSitemap,
}

# --- MODULAR ERROR HANDLERS ---
# We now point to the 'jeba_core' app where we moved these views
handler404 = 'jeba_core.views.custom_404'
handler500 = 'jeba_core.views.custom_500'

urlpatterns = [
    # --- SEO & CRAWLER PATHS (The Missing Keys) ---
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    # ----------------------------------------------
    
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
    # --- NEW AI BUILDER (Add this line) ---
    path('ai/', include('jeba_ai_builder.urls')),
    # --------------------------------------
    path('messenger/', include('jeba_messenger.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)