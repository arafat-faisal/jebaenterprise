from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from django.contrib import messages
from django.db.models import Sum, F 
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from datetime import timedelta
import json
from decimal import Decimal

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
    fields = ('product', 'variation', 'quantity', 'buying_cost', 'sold_price', 'total_price') 
    readonly_fields = ('profit', 'total_price') 

# --- Admin ---
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    # List view still uses the display methods for calculated fields
    list_display = ('order_id', 'customer_name', 'status', 'payment_method', 'display_total_amount', 'display_total_profit', 'consignment_id', 'steadfast_action_button')
    list_filter = ('status', 'created_at', 'payment_method')
    search_fields = ('customer_name', 'phone_number', 'id', 'transaction_id')
    actions = [mark_as_processing]

    # FIX 1: Add the NEW read-only display methods and remove the old ones that caused issues.
    readonly_fields = ('access_token', 'display_order_id', 'calculated_subtotal_display', 'calculated_total_amount_display', 'display_total_profit', 'steadfast_action_button')
    
    # FIX 2: Restructure fieldsets. manual_subtotal and manual_total_amount are the NEW editable fields.
    fieldsets = (
        (None, {
            'fields': (
                ('display_order_id', 'status', 'payment_method'), 
                'access_token', 
                'transaction_id'
            ),
        }),
        ('Order Totals & Overrides (Edit Price)', {
            'fields': (
                ('manual_subtotal', 'manual_total_amount', 'delivery_charge'),
            ),
            'description': 'Enter values here to manually override the totals.'
        }),
        ('Calculated Baseline (Read-Only)', {
            # Display the *actual* automatic calculation based on line items before any overrides.
            'fields': (
                'calculated_subtotal_display',
                'calculated_total_amount_display',
                'display_total_profit',
            ),
            'description': 'These show the system default values based on line items and delivery charge.'
        }),
        ('Customer & Shipping', {
            'fields': ('user', 'customer_name', 'phone_number', 'shipping_address'),
        }),
        ('Courier/Delivery', {
            'fields': (('consignment_id', 'tracking_code'), 'steadfast_action_button'),
        }),
    )

    # Helper method for Order ID (still necessary for property in fieldsets)
    def display_order_id(self, obj):
        return obj.order_id
    display_order_id.short_description = "Order ID"

    # Helper method for Total Amount on the CHANGE LIST view (still necessary)
    def display_total_amount(self, obj):
        # This one is used in list_display and calls the public property (which is now override-aware)
        amount = obj.total_amount if obj.total_amount is not None else Decimal(0)
        return format_html(f"<strong>৳{amount:,.0f}</strong>")
    display_total_amount.short_description = "Total (Inc. Del)"
    display_total_amount.admin_order_field = 'total_amount'

    # NEW: Helper for displaying the non-override subtotal calculation
    def calculated_subtotal_display(self, obj):
        amount = obj._calculated_subtotal if obj._calculated_subtotal is not None else Decimal(0)
        return format_html(f"৳{amount:,.0f}")
    calculated_subtotal_display.short_description = "Auto Subtotal"

    # NEW: Helper for displaying the non-override total calculation
    def calculated_total_amount_display(self, obj):
        amount = obj._calculated_total_amount if obj._calculated_total_amount is not None else Decimal(0)
        return format_html(f"৳{amount:,.0f}")
    calculated_total_amount_display.short_description = "Auto Total"
    
    # Helper method for Total Profit (still necessary)
    def display_total_profit(self, obj):
        profit = obj.total_profit if obj.total_profit is not None else Decimal(0)
        return format_html(f"৳{profit:,.0f}")
    display_total_profit.short_description = "Total Profit"
    display_total_profit.admin_order_field = 'total_profit'


    def get_queryset(self, request):
        qs = super().get_queryset(request).prefetch_related('items')
        return qs

    def steadfast_action_button(self, obj):
        if obj.consignment_id:
            return format_html(
                '<a class="button" style="background-color: #4caf50; color: white;" target="_blank" href="https://portal.steadfast.com.bd/track/{}">Track on Steadfast (ID: {})</a>', 
                obj.consignment_id, obj.consignment_id
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
        sale = get_object_or_404(Sale.objects.prefetch_related('items'), pk=sale_id)
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
                    error_message = result.get('error', 'Unknown error during submission.') 
                    self.message_user(request, f"Error from Steadfast: {error_message}", messages.ERROR)
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
        return render(request, 'admin/sale/send_to_steadfast.html', context)

    def changelist_view(self, request, extra_context=None):
        # Sales Chart Data
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        sales_data = (
            SaleItem.objects
            .filter(
                sale__created_at__range=(start_date, end_date),
                sale__status__in=['SHIPPED', 'DELIVERED'] 
            )
            .annotate(date=TruncDate('sale__created_at'))
            .values('date')
            .annotate(
                daily_revenue=Sum(F('sold_price') * F('quantity'))
            )
            .order_by('date')
        )
        
        dates = [entry['date'].strftime('%Y-%m-%d') for entry in sales_data]
        totals = [float(entry['daily_revenue']) for entry in sales_data]
        
        # Low Stock Warning
        low_stock_products = Product.objects.filter(stock_quantity__lt=5).order_by('stock_quantity')[:5] 

        extra_context = extra_context or {}
        extra_context['chart_dates'] = json.dumps(dates, cls=DjangoJSONEncoder)
        extra_context['chart_totals'] = json.dumps(totals, cls=DjangoJSONEncoder)
        extra_context['low_stock_products'] = low_stock_products
        return super().changelist_view(request, extra_context=extra_context)