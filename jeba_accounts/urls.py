from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'jeba_accounts'

urlpatterns = [
    # --- Custom App Views ---
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('logout/', views.user_logout, name='logout'), # Uses your custom logout view

    # --- Overridden Auth Views (Mapping to Custom Templates) ---
    path('login/', auth_views.LoginView.as_view(
        template_name='jeba_accounts/registration/login.html'
    ), name='login'),

    # Password Reset Workflow
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='jeba_accounts/registration/password_reset_form.html',
        email_template_name='jeba_accounts/registration/password_reset_email.html',
        success_url='done/'
    ), name='password_reset'),

    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='jeba_accounts/registration/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='jeba_accounts/registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='jeba_accounts/registration/password_reset_complete.html'
    ), name='password_reset_complete'),
]