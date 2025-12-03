from django.urls import path
from . import views

urlpatterns = [
    # Shows list of all campaigns at /landing/offers/
    path('offers/', views.landing_page_list, name='landing_page_list'),
    
    # Detail page at /landing/offers/slug/
    path('offers/<slug:slug>/', views.landing_page_detail, name='landing_page_detail'),
    
    path('admin-preview/render/', views.admin_preview, name='admin_preview_render'),
]