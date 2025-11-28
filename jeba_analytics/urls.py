from django.urls import path
from . import views

urlpatterns = [
    path('track-interaction/', views.track_interaction, name='track_interaction'),
    path('track-share/<int:product_id>/', views.track_share, name='track_share'),
]