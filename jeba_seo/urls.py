from django.urls import path
from .views import generate_ai_for_product

urlpatterns = [
    path('generate-ai/<int:product_id>/', generate_ai_for_product, name='generate_ai_product'),
]