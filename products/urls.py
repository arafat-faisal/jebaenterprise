from django.urls import path
from . import views  # We will import 'views' from our app

# This list defines all the pages for the 'products' app
urlpatterns = [
    # This matches the "homepage" (e.g., http://127.0.0.1:8001/)
    # and tells it to run the 'pricing_sheet' function from views.py
    path("", views.pricing_sheet, name="pricing_sheet"),
    path("products/", views.product_catalog, name="product_catalog"), # <--- NEW LINE

    # --- ADD THIS NEW LINE ---
    # This creates a dynamic URL. <int:pk> is a "path converter"
    # that captures an integer (the product's ID, or "Primary Key")
    # and sends it to the view as a variable named 'pk'.
    # e.g., /product/1/  or /product/2/
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    # --- ADD THIS NEW LINE ---
    # This will be the "action" for our add-to-cart button
    path("add-to-cart/<int:product_id>/", views.add_to_cart, name="add_to_cart"),

    # --- ADD THIS NEW LINE ---
    # This will handle adding a specific variation
    path("add-to-cart/var/<int:variation_id>/", views.add_to_cart_variation, name="add_to_cart_variation"),

    path("cart/", views.view_cart, name="view_cart"),
    # --- ADD THESE TWO NEW LINES ---
    path("checkout/", views.checkout, name="checkout"),
    path("order-success/", views.order_success, name="order_success"),
    # --- ADD THIS NEW LINE ---
    path("print-products/", views.print_products_page, name="print_products_page"),
    # --- ADD THIS NEW LINE ---
    path("admin-scraper/", views.admin_scraper_view, name="admin_scraper"),
    # --- ADD THIS NEW LINE ---
    path("register/", views.register_view, name="register"),
    # --- ADD THIS NEW LINE ---
    path("my-orders/", views.my_orders_view, name="my_orders"),

    path("order/<int:pk>/", views.order_detail, name="order_detail"),
    path("search/", views.search_view, name="search"),
    # ... inside urlpatterns ...
    path("user-logout/", views.user_logout, name="user_logout"),
    # ... inside urlpatterns ...
    path("add-review/<int:product_id>/", views.add_review, name="add_review"),
    path("wishlist/toggle/<int:product_id>/", views.toggle_wishlist, name="toggle_wishlist"),
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("profile/", views.profile_view, name="profile"),
]