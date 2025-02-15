from django.urls import path
from .views import create_match_view, attendance_view, payments_view

urlpatterns = [
    path('create-match/', create_match_view, name="manage-create-match"),
    path('attendance/', attendance_view, name="manage-attendance"),
    path('payments/', payments_view, name="manage-payments"),
]
