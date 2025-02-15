from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def create_match_view(request):
    # ...existing code...
    return render(request, 'cric_manage/create_match.html')

@login_required
def attendance_view(request):
    # ...existing code...
    return render(request, 'cric_manage/attendance.html')

@login_required
def payments_view(request):
    # ...existing code...
    return render(request, 'cric_manage/payments.html')
