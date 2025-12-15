from django.urls import path
from . import views

urlpatterns = [
    path('', views.DiagnosticDashboard.as_view(), name='diagnostics_home'),
    path('analyze/', views.analyze_page, name='diagnostics_analyze'),
    path('report/<int:report_id>/', views.report_detail, name='diagnostics_report'),
    path('clear/', views.clear_reports, name='diagnostics_clear'),
]
