from django.urls import path
from . import views

urlpatterns = [
    # Webhook Endpoint
    path('webhook/steadfast/', views.steadfast_webhook, name='steadfast_webhook'),
    
    # Existing views you might want to move here later (optional for now)
]