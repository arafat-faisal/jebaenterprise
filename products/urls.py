from django.urls import path
from django.contrib.auth import views as auth_views

# --- MODULAR VIEW IMPORTS ---
from jeba_inventory import views as inventory_views
from jeba_sales import views as sales_views
from jeba_accounts import views as account_views
from jeba_intelligence import views as intelligence_views
from jeba_engagement import views as engagement_views
from jeba_analytics import views as analytics_views
from jeba_core import views as core_views
# ----------------------------

urlpatterns = [
    # --- Inventory & Catalog ---
    path('', inventory_views.home, name='home'),
    path('catalog/', inventory_views.product_catalog, name='product_catalog'),
    path('product/<int:pk>/', inventory_views.product_detail, name='product_detail'),
    path('search/', inventory_views.search_view, name='search'),
    path('print-products/', inventory_views.print_products_page, name='print_products_page'),

    # --- Sales & Cart ---
    path('cart/', sales_views.view_cart, name='view_cart'),
    path('add-to-cart/<int:product_id>/', sales_views.add_to_cart, name='add_to_cart'),
    path('add-to-cart-variation/<int:variation_id>/', sales_views.add_to_cart_variation, name='add_to_cart_variation'),
    path('update-cart/<str:item_id>/<str:action>/', sales_views.update_cart, name='update_cart'),
    path('checkout/', sales_views.checkout, name='checkout'),
    path('order-success/', sales_views.order_success, name='order_success'),
    path('track-order/<uuid:token>/', sales_views.guest_order_track, name='guest_order_track'),
    
    # --- FIX: Renamed to 'download_invoice_pdf' to match template ---
    path('invoice/<uuid:token>/', sales_views.download_invoice_pdf, name='download_invoice_pdf'),
    
    path('receipt/<uuid:token>/', sales_views.order_receipt, name='order_receipt'),

    # --- User Accounts ---
    path('register/', account_views.register_view, name='register'),
    path('profile/', account_views.profile_view, name='profile'),
    path('dashboard/', account_views.user_dashboard, name='user_dashboard'),
    path('my-orders/', sales_views.my_orders_view, name='my_orders'),
    path('order/<int:pk>/', sales_views.order_detail, name='order_detail'),
    
    # Auth (Standard Django Views)
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', account_views.user_logout, name='user_logout'),
    
    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # --- Engagement (Reviews & Wishlist) ---
    path('add-review/<int:product_id>/', engagement_views.add_review, name='add_review'),
    path('toggle-wishlist/<int:product_id>/', engagement_views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/', engagement_views.wishlist_view, name='wishlist'),

    # --- Analytics (Track Share & Interactions) ---
    path('track-share/<int:product_id>/', analytics_views.track_share, name='track_share'),
    # NEW: General interaction tracking
    path('track-interaction/', analytics_views.track_interaction, name='track_interaction'),

    # --- Intelligence (Admin) ---
    path('admin-tools/scraper/', intelligence_views.admin_scraper_view, name='admin_scraper'),

    # --- Core / Static ---
    path('about/', core_views.about_us, name='about_us'),
    path('contact/', core_views.contact_us, name='contact_us'),
]