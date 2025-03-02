from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role']
        # Add any additional fields that exist on your User model
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control rounded-lg w-full'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control rounded-lg w-full'}),
            'email': forms.EmailInput(attrs={'class': 'form-control rounded-lg w-full'}),
            'role': forms.Select(attrs={'class': 'form-control rounded-lg w-full'}, 
                                choices=[('batsman', 'Batsman'), 
                                         ('bowler', 'Bowler'), 
                                         ('allrounder', 'All-rounder')])
        }

class EmailForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control rounded-lg w-full'})
        }

class UsernameForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control rounded-lg w-full'})
        }