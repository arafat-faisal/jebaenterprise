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
# Note: Ensure products.steadfast exists or move logic to jeba_sales.utils later
from products.steadfast import make_payload, submit_steadfast_order 

# --- ACTIONS ---
@admin.action(description="✓ Mark as Verified/Processing")
def mark_as_processing(modeladmin, request, queryset):
    updated = queryset.update(status='PROCESSING')
    messages.success(request, f"{updated} orders marked as Verified/Processing.")

# --- FORMS ---
class SteadfastReviewForm(forms.Form):
    invoice = forms.CharField(label="Invoice ID", widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'}))
    recipient_name = forms.CharField(max_length=100, label="Customer Name", widget=forms.TextInput(attrs={'class': 'form-control'}))
    recipient_phone = forms.CharField(max_length=15, label="Phone", widget=forms.TextInput(attrs={'class': 'form-control'}))
    recipient_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), label="Address")
    cod_amount = forms.DecimalField(label="COD Amount (Tk)", widget=forms.NumberInput(attrs={'class': 'form-control'})) 
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}), initial="Handle with care")

# --- INLINES ---
class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    fields = ('product', 'variation', 'quantity', 'buying_cost', 'sold_price', 'total_price_display') 
    readonly_fields = ('profit_display', 'total_price_display')
    autocomplete_fields = ['product']

    def total_price_display(self, obj):
        return f"{obj.total_price:,.0f} Tk"
    total_price_display.short_description = "Total"

    def profit_display(self, obj):
        return f"{obj.profit:,.0f} Tk"
    profit_display.short_description = "Profit"

# --- MAIN ADMIN ---
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = (
        'order_id', 
        'customer_name', 
        'phone_number',
        'status_badge', 
        'payment_method', 
        'display_total_amount', 
        'steadfast_action_button'
    )
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('customer_name', 'phone_number', 'id', 'transaction_id', 'access_token')
    actions = [mark_as_processing]
    list_per_page = 20

    # FIX: Added 'steadfast_action_button' to readonly_fields
    readonly_fields = (
        'access_token', 
        'display_order_id',
        'created_at', 
        'calculated_subtotal_display', 
        'calculated_total_amount_display', 
        'display_total_profit', 
        'steadfast_status_preview',
        'invoice_link',
        'steadfast_action_button'  # <--- THIS WAS MISSING
    )
    
    fieldsets = (
        ("📝 Order Details", {
            'fields': (
                ('display_order_id', 'status', 'payment_method'), 
                ('transaction_id', 'created_at'),
                'invoice_link'
            ),
        }),
        ("👤 Customer Info", {
            'fields': (
                ('customer_name', 'phone_number'), 
                'shipping_address', 
                'user'
            ),
        }),
        ("💰 Financials & Overrides", {
            'fields': (
                ('manual_subtotal', 'manual_total_amount', 'delivery_charge'),
                ('calculated_subtotal_display', 'calculated_total_amount_display', 'display_total_profit'),
            ),
            'description': 'Use "Manual" fields to override the automatic sums if necessary.'
        }),
        ("🚚 Courier & Delivery", {
            'fields': (
                ('consignment_id', 'tracking_code'), 
                'steadfast_status_preview',
                'steadfast_action_button' 
            ),
        }),
    )

    # --- CRITICAL FIX: Allow Pre-filling from URL ---
    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        # Capture GET parameters from the Dashboard "Create Order" button
        if request.GET.get('customer_name'):
            initial['customer_name'] = request.GET.get('customer_name')
        if request.GET.get('phone_number'):
            initial['phone_number'] = request.GET.get('phone_number')
        if request.GET.get('shipping_address'):
            initial['shipping_address'] = request.GET.get('shipping_address')
        return initial
    # ------------------------------------------------

    # --- CUSTOM COLUMNS & BADGES ---
    def status_badge(self, obj):
        colors = {
            'PENDING': 'warning',
            'PROCESSING': 'info',
            'SHIPPED': 'primary',
            'DELIVERED': 'success',
            'CANCELLED': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>', 
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def display_order_id(self, obj):
        return obj.order_id
    display_order_id.short_description = "Order ID"

    def display_total_amount(self, obj):
        amount = obj.total_amount if obj.total_amount is not None else Decimal(0)
        return format_html(f"<strong>{amount:,.0f} Tk</strong>")
    display_total_amount.short_description = "Grand Total"
    display_total_amount.admin_order_field = 'manual_total_amount'

    def display_total_profit(self, obj):
        profit = obj.total_profit if obj.total_profit is not None else Decimal(0)
        color = "green" if profit > 0 else "red"
        return format_html(f"<span style='color:{color}; font-weight:bold;'>{profit:,.0f} Tk</span>")
    display_total_profit.short_description = "Total Profit"

    def calculated_subtotal_display(self, obj):
        amount = obj._calculated_subtotal if obj._calculated_subtotal is not None else Decimal(0)
        return f"{amount:,.0f} Tk"
    calculated_subtotal_display.short_description = "Auto Subtotal (Items)"

    def calculated_total_amount_display(self, obj):
        amount = obj._calculated_total_amount if obj._calculated_total_amount is not None else Decimal(0)
        return f"{amount:,.0f} Tk"
    calculated_total_amount_display.short_description = "Auto Total (Items + Del)"

    def invoice_link(self, obj):
        return format_html(
            '<a class="btn btn-sm btn-outline-secondary" href="{}" target="_blank">'
            '<i class="fas fa-file-invoice"></i> View Invoice</a>', 
            # Assuming you have a URL named 'invoice_pdf' or similar. 
            # If not, this link might need adjustment.
            f"/invoice/{obj.access_token}/" 
        )
    invoice_link.short_description = "Invoice"

    # --- STEADFAST INTEGRATION ---
    # --- FIX: ADDED SAFETY CHECK HERE ---
    def steadfast_action_button(self, obj):
        # If the object is being created (has no ID), return a placeholder
        if not obj or not obj.pk:
            return "-"
            
        if obj.consignment_id:
            return format_html('<a class="btn btn-sm btn-success" target="_blank" href="https://portal.steadfast.com.bd/track/{}"><i class="fas fa-truck"></i> Track (ID: {})</a>', obj.consignment_id, obj.consignment_id)
        return format_html('<a class="btn btn-sm btn-primary" href="{}"><i class="fas fa-paper-plane"></i> Send to Courier</a>', reverse('admin:sale_send_steadfast', args=[obj.pk]))
    steadfast_action_button.short_description = "Courier Actions"
    steadfast_action_button.allow_tags = True
    # ------------------------------------

    def steadfast_status_preview(self, obj):
        if obj.consignment_id:
            return format_html('<span style="color:green;">✔ Shipped with Steadfast</span>')
        return format_html('<span style="color:orange;">Not sent yet</span>')
    steadfast_status_preview.short_description = "Courier Status"

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
                # Ensure the payload matches Steadfast API expectations
                # Re-map clean fields to payload keys if necessary
                submission_payload = {
                    'invoice': payload['invoice'],
                    'recipient_name': payload['recipient_name'],
                    'recipient_phone': payload['recipient_phone'],
                    'recipient_address': payload['recipient_address'],
                    'cod_amount': float(payload['cod_amount']),
                    'note': payload['note']
                }
                
                result = submit_steadfast_order(submission_payload)
                
                if result.get('success') or result.get('status') == 200: # Check your submit_steadfast_order return structure
                    # Adapt this based on exactly what submit_steadfast_order returns
                    c_id = result.get('consignment_id') or result.get('consignment', {}).get('consignment_id')
                    t_code = result.get('tracking_code') or result.get('consignment', {}).get('tracking_code')
                    
                    if c_id:
                        sale.consignment_id = c_id
                        sale.tracking_code = t_code
                        sale.status = 'SHIPPED'
                        sale.save()
                        self.message_user(request, f"Successfully created Consignment: {c_id}", messages.SUCCESS)
                        return redirect('admin:jeba_sales_sale_change', sale.id)
                    else:
                         self.message_user(request, f"API success but no ID returned: {result}", messages.WARNING)
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
            'title': f"Send Order #{sale.order_id} to Steadfast",
        }
        return render(request, 'admin/sale/send_to_steadfast.html', context)

    # --- DASHBOARD CHART LOGIC (Preserved) ---
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