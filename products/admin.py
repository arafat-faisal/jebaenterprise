from django.contrib import admin
from django.http import HttpResponseRedirect
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import timedelta

from .models import Product, ProductVariation, Sale, SaleItem, ProductImage, CompetitorPrice, Category, SiteSettings

from django.contrib import messages
from .steadfast import create_steadfast_order # Import our new helper

from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from django.contrib import messages

from .models import Product, ProductVariation, Sale, SaleItem, ProductImage, CompetitorPrice, Category
from .steadfast import create_steadfast_order, make_payload, submit_steadfast_order


# --- 1. Existing Inlines (No Changes) ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    # Explicitly show both fields so you can upload them separately
    fields = ('image', 'transparent_image')

class CompetitorPriceInline(admin.TabularInline):
    model = CompetitorPrice
    extra = 0
    readonly_fields = ('website_name', 'min_price', 'max_price', 'last_checked')
    can_delete = True

class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    fields = ('product', 'variation', 'quantity', 'buying_cost', 'sold_price')

# --- 2. Admin Actions (No Changes) ---
# --- ACTION 1: CONFIRM ORDER ---
@admin.action(description="Confirm Order (Mark Processing)")
def mark_as_processing(modeladmin, request, queryset):
    # Updates status to PROCESSING
    queryset.update(status='PROCESSING')
    messages.success(request, "Selected orders marked as Verified/Processing.")

@admin.action(description="Print selected products")
def print_selected_products(modeladmin, request, queryset):
    selected_ids = ",".join(str(product.id) for product in queryset)
    return HttpResponseRedirect(f"/print-products/?ids={selected_ids}")

# --- 3. Product Admin (No Changes) ---
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductVariationInline, CompetitorPriceInline]
    fieldsets = (
        (None, {'fields': ('name', 'description', 'category', 'is_featured')}), # Added is_featured
        ('Pricing', {'fields': ('buying_cost', 'selling_price')}),
        ('Stock', {'fields': ('stock_quantity', 'box_quantity')}),
    )
    # Update list display to show the checkmark
    list_display = ('name', 'selling_price', 'stock_quantity', 'category', 'is_featured')
    list_editable = ('selling_price', 'stock_quantity', 'is_featured') # Allow quick toggling
    list_filter = ('is_featured', 'category') # Filter by featured
    actions = [print_selected_products]



# --- NEW ACTION ---
# --- ACTION 2: SEND TO COURIER ---
@admin.action(description="Send to Steadfast Courier")
def send_to_courier(modeladmin, request, queryset):
    success_count = 0
    for sale in queryset:
        # Skip if already sent (has ID)
        if sale.consignment_id:
            continue
        
        # Call the API
        result = create_steadfast_order(sale)
        
        if result['success']:
            # Save the Steadfast Data
            sale.consignment_id = result['consignment_id']
            sale.tracking_code = result['tracking_code']
            
            # We set local status to 'SHIPPED' to indicate it's left the warehouse
            # But the user will see the LIVE status from Steadfast
            sale.status = 'SHIPPED' 
            sale.save()
            success_count += 1
        else:
            messages.error(request, f"Failed to send Order {sale.order_id}: {result.get('error')}")
    
    if success_count > 0:
        messages.success(request, f"Successfully sent {success_count} orders to Steadfast.")
# --- FORM FOR EDITING STEADFAST DATA ---
class SteadfastReviewForm(forms.Form):
    invoice = forms.CharField(label="Invoice ID", widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    recipient_name = forms.CharField(max_length=100, label="Customer Name")
    recipient_phone = forms.CharField(max_length=15, label="Phone")
    recipient_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label="Address")
    cod_amount = forms.DecimalField(label="COD Amount (Tk)")
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}), initial="Handle with care")

# --- 4. NEW: Smart Sales Admin Dashboard ---
class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = ('order_id', 'customer_name', 'status', 'payment_method', 'consignment_id', 'total_profit')
    list_filter = ('status', 'created_at', 'payment_method')
    search_fields = ('customer_name', 'phone_number', 'id', 'transaction_id')
    
    # 1. ADD CUSTOM BUTTON FIELD
    readonly_fields = ('total_profit', 'steadfast_action_button')

    actions = ['mark_as_processing'] # We removed the bulk send action to encourage review, or you can keep it.

    # 2. DEFINE THE BUTTON
    def steadfast_action_button(self, obj):
        if obj.consignment_id:
            return format_html(
                '<a class="button" style="background-color: #4caf50; color: white;" target="_blank" href="https://portal.packzy.com/">Track on Steadfast (ID: {})</a>',
                obj.consignment_id
            )
        return format_html(
            '<a class="button" style="background-color: #3F51B5; color: white;" href="{}">Review & Send to Steadfast</a>',
            reverse('admin:send-steadfast', args=[obj.pk])
        )
    steadfast_action_button.short_description = "Courier Actions"
    steadfast_action_button.allow_tags = True

    # 3. REGISTER CUSTOM URL
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:sale_id>/send-steadfast/',
                self.admin_site.admin_view(self.send_to_steadfast_view),
                name='send-steadfast',
            ),
        ]
        return custom_urls + urls

    # 4. THE CUSTOM VIEW (The "Edit Page")
    def send_to_steadfast_view(self, request, sale_id):
        sale = get_object_or_404(Sale, pk=sale_id)
        
        if request.method == 'POST':
            form = SteadfastReviewForm(request.POST)
            if form.is_valid():
                # Get cleaned data
                payload = form.cleaned_data
                
                # Send to API
                result = submit_steadfast_order(payload)
                
                if result['success']:
                    # Save result to DB
                    sale.consignment_id = result['consignment_id']
                    sale.tracking_code = result['tracking_code']
                    sale.status = 'SHIPPED'
                    sale.save()
                    
                    self.message_user(request, f"Successfully created Consignment: {sale.consignment_id}", messages.SUCCESS)
                    return redirect('admin:products_sale_change', sale.id)
                else:
                    self.message_user(request, f"Error from Steadfast: {result.get('error')}", messages.ERROR)
        
        else:
            # Pre-fill form with Sale data
            initial_data = make_payload(sale)
            form = SteadfastReviewForm(initial=initial_data)

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'sale': sale,
            'form': form,
            'title': f"Send Order {sale.order_id} to Steadfast",
        }
        return render(request, 'admin/products/sale/send_to_steadfast.html', context)
    

    # This function injects chart data into the admin page
    def changelist_view(self, request, extra_context=None):
        # A. Calculate Sales for Last 30 Days
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

        # Format data for Chart.js
        dates = [entry['date'].strftime('%Y-%m-%d') for entry in sales_data]
        totals = [float(entry['total_sales']) for entry in sales_data]

        # B. Find Low Stock Products (Threshold < 5)
        low_stock_products = Product.objects.filter(stock_quantity__lt=5)[:5]

        # C. Pass data to the template
        extra_context = extra_context or {}
        extra_context['chart_dates'] = json.dumps(dates, cls=DjangoJSONEncoder)
        extra_context['chart_totals'] = json.dumps(totals, cls=DjangoJSONEncoder)
        extra_context['low_stock_products'] = low_stock_products

        return super().changelist_view(request, extra_context=extra_context)

# --- 5. Register Models ---
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductVariation)
admin.site.register(Sale, SaleAdmin)
admin.site.register(Category)


# Register the Settings model
@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    # Only allow changing, not adding/deleting (since it's a singleton)
    def has_add_permission(self, request):
        # Only allow adding if none exists
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False