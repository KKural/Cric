from django.urls import path
from cric_home.views import *

urlpatterns = [
    path('', home_view, name="home"),
    path('match/<int:match_id>/', match_detail_view, name='match_detail'),
]