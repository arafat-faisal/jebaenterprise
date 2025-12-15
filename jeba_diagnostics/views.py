from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from .models import PageReport
from .utils import analyze_page_performance
from django.urls import reverse

class SuperUserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class DiagnosticDashboard(SuperUserRequiredMixin, View):
    def get(self, request):
        reports = PageReport.objects.all()
        # Suggest valid URLs to test
        suggested_urls = [
            '/',
            '/landing/offers/',
        ]
        return render(request, 'jeba_diagnostics/dashboard.html', {
            'reports': reports,
            'suggested_urls': suggested_urls
        })

def analyze_page(request):
    if not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('/')
        
    if request.method == 'POST':
        url = request.POST.get('url')
        if not url:
            messages.error(request, "URL is required")
            return redirect('diagnostics_home')
            
        # Run Analysis
        data = analyze_page_performance(url, request)
        
        # Save Report
        report = PageReport.objects.create(
            url=data['url'],
            total_time_ms=data['total_time'],
            ttfb_ms=data['ttfb'],
            html_size_bytes=data['html_size'],
            # Approximations for summary
            image_count=len(data['images']),
            script_count=len(data['scripts']),
            performance_score=data['score'],
            details=data
        )
        
        messages.success(request, f"Analysis complete for {url}. Score: {data['score']}/100")
        return redirect('diagnostics_report', report_id=report.id)
        
    return redirect('diagnostics_home')

def report_detail(request, report_id):
    if not request.user.is_superuser:
        return redirect('/')
    report = get_object_or_404(PageReport, id=report_id)
    return render(request, 'jeba_diagnostics/report_detail.html', {'report': report})

def clear_reports(request):
    if request.user.is_superuser:
        PageReport.objects.all().delete()
        messages.success(request, "All reports cleared.")
    return redirect('diagnostics_home')
