from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator

# --- MODULAR IMPORTS ---
from jeba_sales.models import Sale
from jeba_inventory.models import Product
from jeba_engagement.models import Review
from jeba_accounts.models import UserProfile

class CheckoutForm(forms.ModelForm):
    DELIVERY_OPTIONS = [
        ('INSIDE', 'Inside Dhaka (৳60)'),
        ('OUTSIDE', 'Outside Dhaka (৳120)'),
    ]
    delivery_area = forms.ChoiceField(
        choices=DELIVERY_OPTIONS, 
        widget=forms.RadioSelect(attrs={'class': 'delivery-radio'}),
        initial='INSIDE',
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
        fields = ['customer_name', 'phone_number', 'shipping_address', 'payment_method', 'transaction_id']
        widgets = {
            'shipping_address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

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

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your review...', 'class': 'form-control'}),
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'form-control'}),
        }

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'address']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False, help_text="Optional. Recommended for order tracking.", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(required=True, max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=True, max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name'] # Password fields are added by UserCreationForm automatically

    def clean(self):
        # UserCreationForm handles password matching automatically, 
        # so we don't need to manually check it unless you have custom logic.
        return super().clean()