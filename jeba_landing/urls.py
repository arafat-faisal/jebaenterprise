from django.urls import path
from . import views

urlpatterns = [
    # 1. Public Pages
    path('offers/', views.landing_page_list, name='landing_page_list'),
    path('offers/<slug:slug>/', views.landing_page_detail, name='landing_page_detail'),
    
    # 2. Admin Tools
    path('admin-preview/render/', views.admin_preview, name='admin_preview_render'),
    
    # 3. AI Generator (Restored!)
    path('ai/generate/<int:pk>/', views.trigger_ai_generation, name='landing_ai_generate'),
]