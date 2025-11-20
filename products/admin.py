from django.contrib import admin
from django.http import HttpResponseRedirect
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
from datetime import timedelta
import json

from import_export.admin import ImportExportModelAdmin
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget

# Import all models
from .models import (
    Category, Product, ProductVariation, Sale, SaleItem, 
    ProductImage, SiteSettings, CompetitorPrice, Review, 
    Wishlist, UserProfile, ProductEvent, SearchEvent
)

from .steadfast import create_steadfast_order, make_payload, submit_steadfast_order
from .utils import fetch_competitor_data

# --- RESOURCE FOR IMPORT/EXPORT ---
class ProductResource(resources.ModelResource):
    category = Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'name')
    )

    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'short_description', 'category', 'buying_cost', 
                  'selling_price', 'stock_quantity', 'box_quantity', 
                  'is_featured', 'call_for_price')
        import_id_fields = ('id',)


# --- ADMIN ACTIONS ---

@admin.action(description='Auto-Assign Categories (AI-Lite)')
def auto_categorize_products(modeladmin, request, queryset):
    count = 0
    for product in queryset:
        if product.auto_assign_category():
            count += 1
    messages.success(request, f"Successfully categorized {count} products.")

@admin.action(description='Apply Smart Pricing (Comp. Avg - 50)')
def apply_smart_pricing(modeladmin, request, queryset):
    count = 0
    for product in queryset:
        if product.apply_dynamic_pricing():
            count += 1
    messages.success(request, f"Updated prices for {count} products based on competitors.")

# --- NEW ACTION: FIX CALL FOR PRICE ---
@admin.action(description="Fix 'Call for Price' (Disable if Price > 0)")
def fix_call_for_price(modeladmin, request, queryset):
    # Filter those that have a price but still require 'call for price'
    to_fix = queryset.filter(call_for_price=True, selling_price__gt=0)
    count = to_fix.count()
    # Bulk update
    to_fix.update(call_for_price=False)
    messages.success(request, f"Removed 'Call for Price' from {count} priced products.")

@admin.action(description="Confirm Order (Mark Processing)")
def mark_as_processing(modeladmin, request, queryset):
    queryset.update(status='PROCESSING')
    messages.success(request, "Selected orders marked as Verified/Processing.")

@admin.action(description="Print selected products")
def print_selected_products(modeladmin, request, queryset):
    selected_ids = ",".join(str(product.id) for product in queryset)
    return HttpResponseRedirect(f"/print-products/?ids={selected_ids}")

@admin.action(description="Send to Steadfast Courier")
def send_to_courier(modeladmin, request, queryset):
    success_count = 0
    for sale in queryset:
        if sale.consignment_id:
            continue
        result = create_steadfast_order(sale)
        if result['success']:
            sale.consignment_id = result['consignment_id']
            sale.tracking_code = result['tracking_code']
            sale.status = 'SHIPPED' 
            sale.save()
            success_count += 1
        else:
            messages.error(request, f"Failed to send Order {sale.order_id}: {result.get('error')}")
    if success_count > 0:
        messages.success(request, f"Successfully sent {success_count} orders to Steadfast.")

@admin.action(description="Auto-Check Competitor Prices (Heavy)")
def scrape_selected_products(modeladmin, request, queryset):
    success_count = 0
    fail_count = 0
    
    if queryset.count() > 5:
        messages.warning(request, "Please select fewer than 5 products at a time to prevent server timeout.")
        return

    for product in queryset:
        result = fetch_competitor_data(product)
        if result['success']:
            success_count += 1
        else:
            fail_count += 1
            
    messages.success(request, f"Scraping Complete: Updated {success_count} products. Failed/No Data: {fail_count}.")


# --- INLINES ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
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
    extra = 0
    fields = ('product', 'variation', 'quantity', 'buying_cost', 'sold_price')
    readonly_fields = ('profit',)


# --- MAIN ADMIN CLASSES ---

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    inlines = [ProductImageInline, ProductVariationInline, CompetitorPriceInline]
    
    fieldsets = (
        (None, {'fields': ('name', 'category', 'is_featured', 'call_for_price')}),
        ('Descriptions', {'fields': ('short_description', 'description')}),
        ('Pricing', {'fields': ('buying_cost', 'selling_price')}),
        ('Stock', {'fields': ('stock_quantity', 'box_quantity')}),
    )
    
    list_display = ('name', 'selling_price', 'stock_quantity', 'category', 'is_featured', 'call_for_price', 'open_scraper_button')
    list_editable = ('selling_price', 'stock_quantity', 'is_featured', 'call_for_price')
    list_filter = ('is_featured', 'category', 'call_for_price')
    search_fields = ('name', 'description')
    
    actions = [
        print_selected_products, 
        auto_categorize_products, 
        apply_smart_pricing,
        scrape_selected_products,
        fix_call_for_price # <--- Added here
    ]

    def open_scraper_button(self, obj):
        url = reverse('admin_scraper') + f'?product_id={obj.id}'
        return format_html(
            '<a class="button" style="background-color: #17a2b8; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;" href="{}">Visual Match</a>',
            url
        )
    open_scraper_button.short_description = "Manual Tool"
    open_scraper_button.allow_tags = True


# Form for Editing Steadfast Data
class SteadfastReviewForm(forms.Form):
    invoice = forms.CharField(label="Invoice ID", widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    recipient_name = forms.CharField(max_length=100, label="Customer Name")
    recipient_phone = forms.CharField(max_length=15, label="Phone")
    recipient_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label="Address")
    cod_amount = forms.DecimalField(label="COD Amount (Tk)")
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}), initial="Handle with care")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    list_display = ('order_id', 'customer_name', 'status', 'payment_method', 'consignment_id', 'total_profit')
    list_filter = ('status', 'created_at', 'payment_method')
    search_fields = ('customer_name', 'phone_number', 'id', 'transaction_id')
    readonly_fields = ('total_profit', 'steadfast_action_button')
    actions = [mark_as_processing, send_to_courier]

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
                    return redirect('admin:products_sale_change', sale.id)
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
        return render(request, 'admin/products/sale/send_to_steadfast.html', context)

    def changelist_view(self, request, extra_context=None):
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
        low_stock_products = Product.objects.filter(stock_quantity__lt=5)[:5]

        extra_context = extra_context or {}
        extra_context['chart_dates'] = json.dumps(dates, cls=DjangoJSONEncoder)
        extra_context['chart_totals'] = json.dumps(totals, cls=DjangoJSONEncoder)
        extra_context['low_stock_products'] = low_stock_products
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('E-commerce Settings', {
            'fields': ('meta_pixel_id', 'meta_access_token', 'delivery_charge_inside', 'delivery_charge_outside', 'messenger_username', 'facebook_page_url')
        }),
        ('Contact & Support', {
            'fields': ('contact_phone', 'contact_email', 'contact_address', 'business_hours', 'whatsapp_number', 'contact_message_template')
        }),
    )
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False


# --- ANALYTICS PROXY MODEL ---
class ProductAnalytics(Product):
    class Meta:
        proxy = True
        verbose_name = "Product Analytics (Winning Products)"
        verbose_name_plural = "Product Analytics (Winning Products)"

@admin.register(ProductAnalytics)
class WinningProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'total_views', 'total_carts', 'total_orders', 'cart_conversion_rate', 'sales_conversion_rate')
    search_fields = ('name',)
    list_per_page = 50

    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            views=Count('events', filter=Q(events__event_type='VIEW')),
            carts=Count('events', filter=Q(events__event_type='CART')),
            orders=Count('events', filter=Q(events__event_type='PURCHASE')),
        )
        return qs.order_by('-orders', '-carts', '-views')

    def total_views(self, obj): return obj.views
    total_views.admin_order_field = 'views'

    def total_carts(self, obj): return obj.carts
    total_carts.admin_order_field = 'carts'

    def total_orders(self, obj): return obj.orders
    total_orders.admin_order_field = 'orders'

    def cart_conversion_rate(self, obj):
        if obj.views == 0: return "0%"
        return f"{((obj.carts / obj.views) * 100):.1f}%"

    def sales_conversion_rate(self, obj):
        if obj.views == 0: return "0%"
        return f"{((obj.orders / obj.views) * 100):.1f}%"


# --- OTHER REGISTRATIONS ---
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(CompetitorPrice)
class CompetitorPriceAdmin(admin.ModelAdmin):
    list_display = ('product', 'website_name', 'min_price', 'max_price', 'last_checked')
    list_filter = ('website_name',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')

@admin.register(ProductEvent)
class ProductEventAdmin(admin.ModelAdmin):
    list_display = ('product', 'event_type', 'user', 'created_at')
    list_filter = ('event_type', 'created_at')

@admin.register(SearchEvent)
class SearchEventAdmin(admin.ModelAdmin):
    list_display = ('query', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('query',)

# Register simple models that don't need custom admins
admin.site.register(ProductVariation)