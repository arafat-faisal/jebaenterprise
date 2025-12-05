from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

# --- MODULAR IMPORTS ---
from jeba_sales.models import Sale
from jeba_inventory.models import Product, ProductVariation

class CheckoutForm(forms.ModelForm):
    # --- Enforce Required Fields ---
    customer_name = forms.CharField(
        required=True,
        label="Full Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'})
    )
    phone_number = forms.CharField(
        required=True,
        label="Phone Number",
        validators=[
            RegexValidator(
                regex=r'^(\+8801|01)[3-9]\d{8}$',
                message="Enter a valid Bangladeshi phone number (e.g., 01712345678)."
            )
        ],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 01712345678'})
    )
    shipping_address = forms.CharField(
        required=True,
        label="Shipping Address",
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Enter full address'})
    )
    # -------------------------------

    DELIVERY_OPTIONS = [
        ('INSIDE', 'Inside Dhaka (৳60)'),
        ('OUTSIDE', 'Outside Dhaka (৳120)'),
    ]
    
    delivery_area = forms.ChoiceField(
        choices=DELIVERY_OPTIONS, 
        widget=forms.RadioSelect(attrs={'class': 'delivery-radio'}),
        label="Delivery Area"
    )

    payment_method = forms.ChoiceField(
        choices=Sale.PAYMENT_METHODS,
        widget=forms.RadioSelect(attrs={'class': 'payment-radio'}),
        initial='COD',
        label="Payment Method"
    )
    
    transaction_id = forms.CharField(
        required=False, 
        label="TrxID (For bKash)",
        widget=forms.TextInput(attrs={'placeholder': 'e.g. 9G7H6K'}),
        validators=[
            RegexValidator(
                regex='^[A-Za-z0-9]{8,15}$',
                message='Invalid TrxID. It should be 8-15 alphanumeric characters.'
            )
        ]
    )

    class Meta:
        model = Sale
        fields = ['customer_name', 'phone_number', 'shipping_address', 'payment_method', 'transaction_id', 'delivery_area']

    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get('payment_method')
        trx_id = cleaned_data.get('transaction_id')

        # Business Logic: Require TrxID only if bKash is selected
        if method == 'BKASH':
            if not trx_id:
                self.add_error('transaction_id', "Transaction ID is required for bKash payment.")
            else:
                cleaned_data['transaction_id'] = trx_id.upper()
        
        return cleaned_data

# --- NEW: Cart Validation Form (For Variation Upgrade) ---
class AddToCartForm(forms.Form):
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    variation_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    quantity = forms.IntegerField(min_value=1, initial=1)

    def clean(self):
        cleaned_data = super().clean()
        product_id = cleaned_data.get('product_id')
        variation_id = cleaned_data.get('variation_id')
        quantity = cleaned_data.get('quantity') or 1

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            raise ValidationError("Product not found or unavailable.")

        # Variation Validation
        if variation_id:
            try:
                variation = ProductVariation.objects.get(id=variation_id, product=product)
                if not variation.is_active:
                    raise ValidationError("This variation is currently unavailable.")
                
                # Check Stock
                if variation.stock_quantity < quantity:
                     raise ValidationError(f"Only {variation.stock_quantity} left in stock for this option.")
            except ProductVariation.DoesNotExist:
                raise ValidationError("Invalid variation selected.")
        else:
            # Check Product Stock (No variation)
            # Only if product has NO variations active should we check main stock here usually,
            # but usually we check stock_quantity of the main product:
            if product.stock_quantity < quantity:
                raise ValidationError(f"Only {product.stock_quantity} left in stock.")

        return cleaned_data