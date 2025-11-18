from django import forms
from .models import Sale

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer_name', 'phone_number', 'shipping_address']
        widgets = {
            'customer_name': forms.TextInput(attrs={'placeholder': 'Full Name', 'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'placeholder': '017...', 'class': 'form-control'}),
            'shipping_address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Street, City, Zip Code', 'class': 'form-control'}),
        }