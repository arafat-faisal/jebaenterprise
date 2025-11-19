from django import forms
from django.core.validators import RegexValidator
from .models import Sale

from .models import Review, UserProfile
from django.contrib.auth.models import User

from django.contrib.auth.forms import UserCreationForm  # Import this at the top if not already there


class CheckoutForm(forms.ModelForm):
    # --- NEW LOCATION FIELD ---
    DELIVERY_OPTIONS = [
        ('INSIDE', 'Inside Dhaka (৳60)'),
        ('OUTSIDE', 'Outside Dhaka (৳120)'),
    ]
    delivery_area = forms.ChoiceField(
        choices=DELIVERY_OPTIONS, 
        widget=forms.RadioSelect(attrs={'class': 'delivery-radio'}),
        initial='INSIDE'
    )
    # --------------------------

    # We define payment_method explicitly to use a RadioSelect widget
    payment_method = forms.ChoiceField(
        choices=Sale.PAYMENT_METHODS,
        widget=forms.RadioSelect(attrs={'class': 'payment-radio'}),
        initial='COD'
    )
    
    # --- FIX: Add 'widget' here to restore the styling ---
    transaction_id = forms.CharField(
        required=False, 
        validators=[
            RegexValidator(
                regex='^[A-Za-z0-9]{8,15}$',
                message='Invalid TrxID. It should be 8-15 alphanumeric characters (e.g., 9G7H6K).'
            )
        ],
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. 8N7A6D5...', 
            'class': 'form-control',          # <--- This applies your CSS style
            'style': 'text-transform: uppercase;' 
        })
    )
    # -----------------------------------------------------

    class Meta:
        model = Sale
        fields = ['customer_name', 'phone_number', 'shipping_address', 'payment_method', 'transaction_id']
        widgets = {
            'customer_name': forms.TextInput(attrs={'placeholder': 'Full Name', 'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'placeholder': '017...', 'class': 'form-control'}),
            'shipping_address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Street, City, Zip Code', 'class': 'form-control'}),
            # We removed 'transaction_id' from here because it's defined above now
        }

    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get('payment_method')
        trx_id = cleaned_data.get('transaction_id')

        if method == 'BKASH':
            if not trx_id:
                self.add_error('transaction_id', "Transaction ID is required for bKash payment.")
            else:
                # Force Uppercase for consistency
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

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }


# --- NEW: Custom Sign Up Form ---
class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False, help_text="Optional. Recommended for order tracking.")
    first_name = forms.CharField(required=True, max_length=30)
    last_name = forms.CharField(required=True, max_length=30)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')