from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from django.contrib import messages
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from datetime import timedelta
import json

# --- Models ---
from jeba_sales.models import Sale, SaleItem
from jeba_inventory.models import Product

# --- Utils ---
from products.steadfast import make_payload, submit_steadfast_order

# --- Actions ---
@admin.action(description="Confirm Order (Mark Processing)")
def mark_as_processing(modeladmin, request, queryset):
    queryset.update(status='PROCESSING')
    messages.success(request, "Selected orders marked as Verified/Processing.")

# --- Forms ---
class SteadfastReviewForm(forms.Form):
    invoice = forms.CharField(label="Invoice ID", widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    recipient_name = forms.CharField(max_length=100, label="Customer Name")
    recipient_phone = forms.CharField(max_length=15, label="Phone")
    recipient_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label="Address")
    cod_amount = forms.DecimalField(label="COD Amount (Tk)")
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}), initial="Handle with care")

# --- Inlines ---
class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    fields = ('product', 'variation', 'quantity', 'buying_cost', 'sold_price')
    readonly_fields = ('profit',)

# --- Admin ---
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = ('order_id', 'customer_name', 'status', 'payment_method', 'consignment_id', 'total_profit')
    list_filter = ('status', 'created_at', 'payment_method')
    search_fields = ('customer_name', 'phone_number', 'id', 'transaction_id')
    readonly_fields = ('total_profit', 'steadfast_action_button')
    actions = [mark_as_processing]

    def steadfast_action_button(self, obj):
        if obj.consignment_id:
            return format_html(
                '<a class="button" style="background-color: #4caf50; color: white;" target="_blank" href="https://portal.packzy.com/">Track on Steadfast (ID: {})</a>',
                obj.consignment_id
            )
        return format_html(
            '<a class="button" style="background-color: #3F51B5; color: white;" href="{}">Review & Send to Steadfast</a>',
            reverse('admin:sale_send_steadfast', args=[obj.pk])
        )
    steadfast_action_button.short_description = "Courier Actions"
    steadfast_action_button.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:sale_id>/send-steadfast/',
                self.admin_site.admin_view(self.send_to_steadfast_view),
                name='sale_send_steadfast',
            ),
        ]
        return custom_urls + urls

    def send_to_steadfast_view(self, request, sale_id):
        sale = get_object_or_404(Sale, pk=sale_id)
        if request.method == 'POST':
            form = SteadfastReviewForm(request.POST)
            if form.is_valid():
                payload = form.cleaned_data
                result = submit_steadfast_order(payload)
                if result['success']:
                    sale.consignment_id = result['consignment_id']
                    sale.tracking_code = result['tracking_code']
                    sale.status = 'SHIPPED'
                    sale.save()
                    self.message_user(request, f"Successfully created Consignment: {sale.consignment_id}", messages.SUCCESS)
                    return redirect('admin:jeba_sales_sale_change', sale.id)
                else:
                    self.message_user(request, f"Error from Steadfast: {result.get('error')}", messages.ERROR)
        else:
            initial_data = make_payload(sale)
            form = SteadfastReviewForm(initial=initial_data)

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'sale': sale,
            'form': form,
            'title': f"Send Order {sale.order_id} to Steadfast",
        }
        return render(request, 'admin/jeba_sales/sale/send_to_steadfast.html', context)

    def changelist_view(self, request, extra_context=None):
        # Sales Chart Data
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        sales_data = (
            SaleItem.objects
            .filter(sale__created_at__range=(start_date, end_date))
            .annotate(date=TruncDate('sale__created_at'))
            .values('date')
            .annotate(total_sales=Sum('sold_price'))
            .order_by('date')
        )
        dates = [entry['date'].strftime('%Y-%m-%d') for entry in sales_data]
        totals = [float(entry['total_sales']) for entry in sales_data]
        
        # Low Stock Warning
        low_stock_products = Product.objects.filter(stock_quantity__lt=5)[:5]

        extra_context = extra_context or {}
        extra_context['chart_dates'] = json.dumps(dates, cls=DjangoJSONEncoder)
        extra_context['chart_totals'] = json.dumps(totals, cls=DjangoJSONEncoder)
        extra_context['low_stock_products'] = low_stock_products
        return super().changelist_view(request, extra_context=extra_context)