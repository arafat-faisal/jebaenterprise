from django import forms
from django.core.validators import RegexValidator
from jeba_sales.models import Sale

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
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your phone number'})
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
    
    # MODIFIED: Removed initial='INSIDE' to force user selection
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

        if method == 'BKASH':
            if not trx_id:
                self.add_error('transaction_id', "Transaction ID is required for bKash payment.")
            else:
                cleaned_data['transaction_id'] = trx_id.upper()
        
        return cleaned_data