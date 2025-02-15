from django.urls import path
from cric_home.views import *

urlpatterns = [
    path('', home_view, name="home"),  
]