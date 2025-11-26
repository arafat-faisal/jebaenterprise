from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from jeba_accounts.models import UserProfile

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
        fields = ['username', 'email', 'first_name', 'last_name']

    def clean(self):
        return super().clean()