from django.urls import path
from . import views

urlpatterns = [
    # ... existing urls ...
    path('api/search-suggestions/', views.search_suggestions_api, name='search_suggestions_api'),
]