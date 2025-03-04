from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),  # Admin panel
    path('login/', auth_views.LoginView.as_view(template_name='account/login.html'), name='login'),  # Login page
]
