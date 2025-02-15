from django.shortcuts import render, redirect, get_object_or_404
# redirect_to_login
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse
# from allauth.account.utils import send_email_confirmation
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db import transaction
from django.db.utils import OperationalError
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from .forms import ProfileForm, EmailForm, UsernameForm


User = get_user_model()

def profile_view(request, username=None):
    if username:
        profile = get_object_or_404(User, username=username).profile
    else:
        # Instead of using a try/except that calls redirect_to_login,
        # check explicitly if the user has a profile.
        if not hasattr(request.user, 'profile'):
            messages.error(request, "Profile not found. Please update your profile settings.")
            return redirect('profile-settings')
        profile = request.user.profile
    return render(request, 'cric_users/profile.html', {'profile':profile})


@login_required
def profile_edit_view(request):
    # Wrap transactional operations in their own atomic block
    try:
        with transaction.atomic():
            form = ProfileForm(instance=request.user.profile)
            if request.method == 'POST':
                form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
                if form.is_valid():
                    form.save()
                    return redirect('profile')
    except Exception as e:
        # The transaction has been rolled back automatically
        messages.error(request, f'An error occurred: {e}')
        return redirect('profile-settings')
    
    onboarding = (request.path == reverse('profile-onboarding'))
    return render(request, 'cric_users/profile_edit.html', {'form': form, 'onboarding': onboarding})


@login_required
def profile_settings_view(request):
    # Changed template path from 'cric_users/profile_settings.html' to 'a_users/profile_settings.html'
    return render(request, 'a_users/profile_settings.html')


@login_required
def profile_emailchange(request):
    
    if request.htmx:
        form = EmailForm(instance=request.user)
        return render(request, 'partials/email_form.html', {'form':form})
    
    if request.method == 'POST':
        form = EmailForm(request.POST, instance=request.user)

        if form.is_valid():
            
            # Check if the email already exists
            email = form.cleaned_data['email']
            if User.objects.filter(email=email).exclude(id=request.user.id).exists():
                messages.warning(request, f'{email} is already in use.')
                return redirect('profile-settings')
            
            form.save() 
            
            # Then Signal updates emailaddress and set verified to False
            
            # Then send confirmation email 
            send_email_confirmation(request, request.user)
            
            return redirect('profile-settings')
        else:
            messages.warning(request, 'Email not valid or already in use')
            return redirect('profile-settings')
        
    return redirect('profile-settings')


@login_required
def profile_usernamechange(request):
    if request.htmx:
        form = UsernameForm(instance=request.user)
        return render(request, 'partials/username_form.html', {'form':form})
    
    if request.method == 'POST':
        form = UsernameForm(request.POST, instance=request.user)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Username updated successfully.')
            return redirect('profile-settings')
        else:
            messages.warning(request, 'Username not valid or already in use')
            return redirect('profile-settings')
    
    return redirect('profile-settings')    


@login_required
def profile_emailverify(request):
    send_email_confirmation(request, request.user)
    return redirect('profile-settings')


@login_required
def profile_delete_view(request):
    user = request.user
    if request.method == "POST":
        logout(request)
        user.delete()
        messages.success(request, 'Account deleted, what a pity')
        return redirect('home')
    
    return render(request, 'cric_users/profile_delete.html')