"""
URL configuration for indcric project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from .views import login_view, dashboard, register_view, Home, matches, match_detail, match_delete, logout_view
from .admin import manage_matches, attendance  # Import the views from admin

urlpatterns = [
    path('', login_view, name='login'),
    path('home/', Home, name='Home'),
    path("admin/", admin.site.urls),
    path('register/', register_view, name='register'),
    path('dashboard/', dashboard, name='dashboard'),
    path('matches/', matches, name='matches'),
    path('match/<int:pk>/', match_detail, name='match_detail'),
    path('match/<int:pk>/delete/', match_delete, name='match_delete'),
    path('matches/manage/', manage_matches, name='manage_matches'),  # added URL pattern
    path('matches/attendance/<int:match_id>/', attendance, name='attendance'),  # updated URL pattern
    path('logout/', logout_view, name='logout'),
]
