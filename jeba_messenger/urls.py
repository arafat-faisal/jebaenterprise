from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.fb_webhook, name='fb_webhook'),
    path('dashboard/', views.chat_dashboard, name='chat_dashboard'),
    path('send/', views.send_reply, name='send_reply'),
    path('api/generate/', views.manual_ai_generate, name='manual_ai_generate'),
    # NEW URL
    path('api/toggle-ai/', views.toggle_auto_ai, name='toggle_auto_ai'),
]