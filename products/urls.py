from django.urls import path
from . import views  # We will import 'views' from our app

# This list defines all the pages for the 'products' app
urlpatterns = [
    # This matches the "homepage" (e.g., http://127.0.0.1:8001/)
    # and tells it to run the 'pricing_sheet' function from views.py
    path("", views.pricing_sheet, name="pricing_sheet"),

    # --- ADD THIS NEW LINE ---
    # This creates a dynamic URL. <int:pk> is a "path converter"
    # that captures an integer (the product's ID, or "Primary Key")
    # and sends it to the view as a variable named 'pk'.
    # e.g., /product/1/  or /product/2/
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
]