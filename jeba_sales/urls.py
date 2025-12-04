from django.urls import path
from . import views

urlpatterns = [
    # Webhook Endpoint
    path('webhook/steadfast/', views.steadfast_webhook, name='steadfast_webhook'),
    
    # NEW: Cart API
    path('cart/api/update/', views.update_cart_api, name='update_cart_api'),
]