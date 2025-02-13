from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.middleware.csrf import get_token
from django.http import HttpResponse, HttpResponseRedirect
from django.db.utils import OperationalError
from django.db.models import Sum
from django.urls import reverse
from datetime import date
from indcric.models import User, Payment, Wallet, Match, Player, Team, Attendance
from .tables import UpcomingMatchTable
import pandas as pd
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('dashboard')
    csrf_token = get_token(request)
    return render(request, 'register.html', {'csrf_token': csrf_token})

def login_view(request):
    if request.method == 'POST':
        try:
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # Redirect to the Dashboard page
                return redirect('dashboard')
            else:
                csrf_token = get_token(request)
                return render(request, 'login.html', {'error': 'Invalid credentials', 'csrf_token': csrf_token})
        except OperationalError:
            return HttpResponse("Database table missing. Please run 'python manage.py migrate'.", status=500)
    csrf_token = get_token(request)
    return render(request, 'login.html', {'csrf_token': csrf_token})

@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
    return render(request, 'logout.html')

@login_required
def Home(request):
    return render(request, 'base.html')

@login_required
def dashboard(request):
    user = request.user
    payments = Payment.objects.filter(user=user)
    advances = Wallet.objects.filter(user=user)
    matches = Match.objects.all()

    # Retrieve wallet amount
    wallet_obj = Wallet.objects.filter(user=user).first()
    wallet_amount = wallet_obj.amount if wallet_obj else 0

    # Upcoming match: first match with date >= today
    upcoming_match = Match.objects.filter(date__gte=date.today()).order_by('date').first()
    upcoming_table_html = None
    if upcoming_match:
        data = [{
            'Name': upcoming_match.name,
            'Date': upcoming_match.date,
            'Time': upcoming_match.time,
            'Duration': upcoming_match.duration,
            'Location': upcoming_match.location,
        }]
        df = pd.DataFrame(data)
        upcoming_table_html = df.to_html(classes="table table-striped table-hover", index=False, border=0)

    # Previous matches: those with date < today
    previous_matches = Match.objects.filter(date__lt=date.today()).order_by('-date')
    prev_matches_info = []
    for match in previous_matches:
        players_team1 = Player.objects.filter(team=match.team1)
        players_team2 = Player.objects.filter(team=match.team2)
        player_users = [p.user for p in players_team1] + [p.user for p in players_team2]
        total_paid = Payment.objects.filter(user__in=player_users, status='paid').aggregate(
            total=Sum('amount')
        )['total'] or 0
        prev_matches_info.append({
            'match': match,
            'date': match.date,
            'total_paid': total_paid,
            'cost': match.cost,
            'location': match.location
        })

    context = {
        'user': user,
        'payments': payments,
        'advances': advances,
        'matches': matches,
        'wallet_amount': wallet_amount,
        'upcoming_match': upcoming_match,
        'upcoming_table_html': upcoming_table_html,  # updated variable
        'previous_matches': prev_matches_info,
        'match_id': upcoming_match.id if upcoming_match else None,  # Pass match_id to context
    }
    return render(request, 'dashboard.html', context)

@login_required
def matches(request):
    matches = Match.objects.all()
    return render(request, 'matches.html', {'matches': matches})

@login_required
def match_detail(request, pk):
    match = get_object_or_404(Match, pk=pk)
    return render(request, 'match_detail.html', {'match': match})

@login_required
def match_delete(request, pk):
    match = get_object_or_404(Match, pk=pk)
    # Delete linked Team and Players if they were created on the fly.
    team1 = match.team1
    team2 = match.team2
    # Delete players linked to team1 and team2
    Player.objects.filter(team=team1).delete()
    Player.objects.filter(team=team2).delete()
    # Delete teams
    team1.delete()
    team2.delete()
    # Finally, delete the match itself
    match.delete()
    return HttpResponseRedirect(reverse('dashboard'))

@staff_member_required
def manage_matches(request):
    return render(request, 'manage_matches.html')

@staff_member_required
def attendance(request, match_id=None):
    selected_match = None
    team1_players = []
    team2_players = []
    attended_player_ids = set()
    match_id = match_id or request.GET.get('match_id') or request.POST.get('match_id')
    recent_matches = Match.objects.order_by('-date')[:3]
    if match_id:
        selected_match = get_object_or_404(Match, pk=match_id)
    else:
        selected_match = recent_matches.first()
    
    if selected_match:
        team1_players = Player.objects.filter(team=selected_match.team1)
        team2_players = Player.objects.filter(team=selected_match.team2)
        if request.method == 'POST':
            # If “attended_...” checkboxes are present, update attendance
            if any(k.startswith('attended_') for k in request.POST.keys()):
                for player in team1_players | team2_players:
                    attended = request.POST.get(f'attended_{player.id}', 'off') == 'on'
                    Attendance.objects.update_or_create(
                        player=player,
                        match=selected_match,
                        defaults={'attended': attended}
                    )
                # Update attended_player_ids after saving attendance
                attended_player_ids = set(
                    Attendance.objects.filter(match=selected_match, attended=True)
                    .values_list('player_id', flat=True)
                )
                return redirect('attendance', match_id=selected_match.id)
        else:
            # Build a set for quick “attended” lookup
            attended_player_ids = set(
                Attendance.objects.filter(match=selected_match, attended=True)
                .values_list('player_id', flat=True)
            )

    context = {
        'recent_matches': recent_matches,
        'selected_match': selected_match,
        'team1_players': team1_players,
        'team2_players': team2_players,
        'attended_player_ids': attended_player_ids,
    }
    return render(request, 'attendance.html', context)

@login_required
def create_users(request: HttpRequest):
    if not request.user.is_staff:
        return render(request, 'admin/unauthorized.html', status=403)
    non_staff_users = User.objects.filter(is_staff=False)
    message = None
    if request.method == "POST":
        if 'users_data' in request.POST:
            users_data = request.POST.get('users_data', '')
            created_users = []
            for line in users_data.splitlines():
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 2:
                    username, password = parts[0], parts[1]
                    email = parts[2] if len(parts) > 2 else ''
                    # Create user (default create_user creates non-staff user)
                    user = User.objects.create_user(username=username, password=password, email=email)
                    created_users.append(user)
            message = f"Created {len(created_users)} users."
            non_staff_users = User.objects.filter(is_staff=False)
        elif 'delete_user' in request.POST:
            user_id = request.POST.get('delete_user')
            user = get_object_or_404(User, id=user_id)
            user.delete()
            message = f"User {user.username} deleted successfully."
            non_staff_users = User.objects.filter(is_staff=False)
    return render(request, 'admin/create_users.html', {'non_staff_users': non_staff_users, 'message': message})

