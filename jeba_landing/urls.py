from django.urls import path
from . import views

urlpatterns = [
    # This matches /offers/your-page-slug/
    path('offers/<slug:slug>/', views.landing_page_detail, name='landing_detail'),
    path('admin-preview/render/', views.admin_preview, name='admin_preview_render'),
]