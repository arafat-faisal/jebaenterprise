from django.urls import path
from . import views

urlpatterns = [
    # The Editor
    path('builder/', views.builder_workspace, name='ai_builder_new'),
    path('builder/<slug:slug>/', views.builder_workspace, name='ai_builder_workspace'),
    
    # The Preview (Clean Page)
    path('preview/<slug:slug>/', views.page_preview, name='ai_page_preview'),
    
    # API
    path('api/chat/<slug:slug>/', views.ai_chat_endpoint, name='ai_chat_endpoint'),
    path('api/publish/<slug:slug>/', views.publish_page, name='ai_page_publish'),
    path('restore/<int:version_id>/', views.restore_version, name='ai_restore_version'),
    
]