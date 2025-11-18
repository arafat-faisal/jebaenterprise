from django import forms
from .models import Sale

from .models import Review, UserProfile
from django.contrib.auth.models import User

from django.contrib.auth.forms import UserCreationForm  # Import this at the top if not already there


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer_name', 'phone_number', 'shipping_address']
        widgets = {
            'customer_name': forms.TextInput(attrs={'placeholder': 'Full Name', 'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'placeholder': '017...', 'class': 'form-control'}),
            'shipping_address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Street, City, Zip Code', 'class': 'form-control'}),
        }

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
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True, max_length=30)
    last_name = forms.CharField(required=True, max_length=30)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')