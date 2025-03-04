from django.urls import path
from .views import user_login, user_logout, dashboard

urlpatterns = [
    path('', user_login, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('logout/', user_logout, name='logout'),
]
