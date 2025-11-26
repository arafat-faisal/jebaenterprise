from django.shortcuts import render, redirect
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
import threading

# --- MODULAR IMPORTS ---
from jeba_sales.models import Sale
# -----------------------

# --- LEGACY IMPORTS (Forms & Utils) ---
# We still pull forms/utils from the old location until we move them in Phase 3
from jeba_accounts.forms import SignUpForm, UserForm, ProfileForm
from jeba_accounts.utils import send_welcome_email

def register_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            if user.email: 
                try:
                    # Send welcome email in background
                    threading.Thread(target=send_welcome_email, args=(user,)).start()
                except:
                    pass 

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = SignUpForm()

    context = {'form': form}
    return render(request, 'registration/register.html', context)

def user_logout(request):
    logout(request)
    # Redirect to homepage (pricing_sheet is the view name for home)
    return redirect('home')

@login_required
def profile_view(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        # Access profile via the related_name 'profile' set in the OneToOneField
        profile_form = ProfileForm(request.POST, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=request.user.profile)
    
    return render(request, 'registration/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

@login_required
def user_dashboard(request):
    user = request.user
    
    # Handle multiple forms on one page
    if request.method == 'POST' and 'update_profile' in request.POST:
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, instance=user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_dashboard')
            
    elif request.method == 'POST' and 'change_password' in request.POST:
        password_form = PasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            # Important: Keep user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Please correct the error below.')
    
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=user.profile)
        password_form = PasswordChangeForm(user)

    # Fetch recent orders for the dashboard widget
    recent_orders = Sale.objects.filter(user=user).order_by('-created_at')[:3]
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form,
        'recent_orders': recent_orders
    }
    return render(request, 'registration/dashboard.html', context)