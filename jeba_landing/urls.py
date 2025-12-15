from django.urls import path
from . import views

urlpatterns = [
    # API (Tracking Beacon)
    path('api/track/', views.TrackEventView.as_view(), name='landing_track_event'),
    
    # Analytics Dashboard
    path('analytics/<slug:slug>/', views.analytics_dashboard, name='landing_analytics_dashboard'),
    
    # Campaign Landing Page (Catch-all for slugs)
    path('offers/', views.campaign_list, name='landing_page_list'),
    path('order/place/', views.place_order, name='landing_place_order'),
    path('<slug:slug>/', views.CampaignDispatchView.as_view(), name='campaign_detail'),
]