from django.urls import path
from . import views

# app_name = 'jeba_sales'  # Namespace for reverse lookups (optional but recommended)

urlpatterns = [
    # --- CART ACTIONS ---
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/add-variation/<int:variation_id>/', views.add_to_cart_variation, name='add_to_cart_variation'),
    path('cart/update/<str:item_id>/<str:action>/', views.update_cart, name='update_cart'),
    
    # --- AJAX API (For Frontend Updates) ---
    path('cart/api/update/', views.update_cart_api, name='update_cart_api'),

    # --- CHECKOUT ---
    path('checkout/', views.checkout, name='checkout'),
    
    # --- ORDER MANAGEMENT ---
    path('order/success/', views.order_success, name='order_success'),
    path('order/<int:pk>/', views.order_detail, name='order_detail'),
    path('track-order/<str:token>/', views.guest_order_track, name='guest_order_track'),
    path('invoice/<str:token>/', views.order_receipt, name='order_receipt'),
    path('invoice/<str:token>/pdf/', views.download_invoice_pdf, name='download_invoice_pdf'),

    # --- WEBHOOKS ---
    path('webhook/steadfast/', views.steadfast_webhook, name='steadfast_webhook'),
    path('cart/api/apply-coupon/', views.apply_coupon_api, name='apply_coupon_api'), # <--- ADD THIS
]