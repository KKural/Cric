import logging
import pdb  # Import pdb for debugging
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect, get_object_or_404  # add redirect and get_object_or_404 import
from django.http import HttpRequest
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required  # add staff_member_required import
from django.db.models import Count  # add Count import
from .models import User, Payment, Wallet, Attendance, Match, Team, Player  # Added Payment, Wallet, Attendance, Match, and Team imports
from decimal import Decimal  # add Decimal import

# Set up logging
logger = logging.getLogger(__name__)

# Define the custom admin view
@login_required
def admin_dashboard(request: HttpRequest):
    if not request.user.is_authenticated:
        logger.warning("User is not authenticated")
    if not request.user.is_staff:
        logger.warning("User does not have staff permissions")
    
    # Query user data and annotate payment/advance and match info
    users = list(User.objects.all())
    # join users with payment, advance, and match info
    for user in users:
        payment = Payment.objects.filter(user=user).first()
        advance = Wallet.objects.filter(user=user).first()
        attendance = Attendance.objects.filter(player__user=user)
        match_ids = attendance.values_list('match_id', flat=True)
        matches = Match.objects.filter(id__in=match_ids)
        user.payment = payment.amount if payment else "N/A"
        user.advance = advance.amount if advance else "N/A"
        user.matches = ", ".join(match.name for match in matches) if matches.exists() else "N/A"
    logger.debug(f"Queried {len(users)} users with payment, advance and match info")
    
    return render(request, 'admin/dashboard.html', {'indcric_users': users})

@login_required
def add_users(request: HttpRequest):
    if not request.user.is_staff:
        return render(request, 'admin/unauthorized.html', status=403)  # or HttpResponse("Unauthorized", status=403)
    if request.method == "POST":
        data = request.POST.get('users_data', '')
        lines = data.splitlines()
        created_users = []
        for line in lines:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 2:
                username, password = parts[0], parts[1]
                email = parts[2] if len(parts) > 2 else ''
                # Create new user
                user = User.objects.create_user(username=username, password=password, email=email)
                created_users.append(user)
        return render(request, 'admin/add_users_success.html', {"created_users": created_users})
    return render(request, 'admin/add_users.html')

@login_required
def add_user(request: HttpRequest):
    if not request.user.is_staff:
        return render(request, 'admin/unauthorized.html', status=403)
    message = None
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        email = request.POST.get('email', '').strip()
        if username and password:
            user = User.objects.create_user(username=username, password=password, email=email)
            message = f"User {user.username} added successfully."
        else:
            message = "Username and password are required."
    return render(request, 'admin/add_user.html', {"message": message})

# Store the original get_urls method
original_get_urls = admin.site.get_urls

@login_required
def create_match(request: HttpRequest):
    if not request.user.is_staff:
        return render(request, 'admin/unauthorized.html', status=403)
    message = None
    teams = Team.objects.all()  # Fetch available teams
    users = User.objects.all()  # Fetch available users for team selection
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        date = request.POST.get('date', '').strip()
        time = request.POST.get('time', '').strip()
        # Extract duration and cast to int, using default 3 if missing or empty
        duration = int(request.POST.get('duration') or 3)
        cost_per_hour = int(request.POST.get('cost_per_hour') or 29)
        cost = duration * cost_per_hour
        location = request.POST.get('location', '').strip()
        # Fetch hidden fields with team assignments from drag-and-drop
        team1_users = request.POST.get('team1_users', '')
        team2_users = request.POST.get('team2_users', '')
        if name and date and time and location:
            team1_name = request.POST.get('team1_name', '').strip() or "Team 1"
            team2_name = request.POST.get('team2_name', '').strip() or "Team 2"
            # Create teams on the fly
            team1 = Team.objects.create(name=team1_name, captain=request.user)
            team2 = Team.objects.create(name=team2_name, captain=request.user)
            match = Match.objects.create(name=name, date=date, time=time, duration=duration, cost=cost, location=location, team1=team1, team2=team2)
            # Convert dropped users to players in each team
            from .models import Player
            if team1_users:
                for uid in team1_users.split(','):
                    if uid.strip():
                        user = User.objects.get(id=uid.strip())
                        # Only create if not already a Player; skip if exists
                        Player.objects.get_or_create(user=user, defaults={'team': team1, 'role': 'player'})
            if team2_users:
                for uid in team2_users.split(','):
                    if uid.strip():
                        user = User.objects.get(id=uid.strip())
                        Player.objects.get_or_create(user=user, defaults={'team': team2, 'role': 'player'})
            return redirect('dashboard')
        else:
            message = "All match fields are required."
    return render(request, 'admin/create_match.html', {"message": message, "teams": teams, "users": users})

@staff_member_required
def update_payments(request: HttpRequest):
    selected_match = None
    team1_players = []
    team2_players = []
    match_id = request.GET.get('match_id') or request.POST.get('match_id')
    recent_matches = Match.objects.order_by('-date')[:3]
    if match_id:
        selected_match = get_object_or_404(Match, pk=match_id)
    else:
        selected_match = recent_matches.first()
    
    if selected_match:
        team1_players = Player.objects.filter(team=selected_match.team1, attendance__match=selected_match, attendance__attended=True)
        team2_players = Player.objects.filter(team=selected_match.team2, attendance__match=selected_match, attendance__attended=True)
        if request.method == 'POST':
            logger.debug(f"POST data: {request.POST}")  # Log POST debug info
            # If “paid_...” checkboxes are present, process payments
            if any(k.startswith('paid_') for k in request.POST.keys()):
                attended_player_qs = Player.objects.filter(
                    attendance__match=selected_match, attendance__attended=True
                ).distinct()
                attended_count = attended_player_qs.count()
                if attended_count > 0:
                    cost_per_player = Decimal(selected_match.cost) / attended_count
                    logger.debug(f"Cost per player: {cost_per_player}")
                    for player in attended_player_qs:
                        field_name = f'paid_{player.id}'
                        if field_name in request.POST:
                            wallet = Wallet.objects.filter(user=player.user).first()
                            if wallet:
                                # Check if payment already exists
                                payment_exists = Payment.objects.filter(user=player.user, match=selected_match).exists()
                                if not payment_exists and wallet.status == 'pending':
                                    # If wallet insufficient, allow negative or mark as cash
                                    if wallet.amount >= cost_per_player:
                                        wallet.amount -= cost_per_player
                                        new_method = 'wallet'
                                        status = 'paid'
                                    elif wallet.amount < 0:
                                        new_method = 'overdraft'
                                        status = 'pending'
                                        # should not be paid until the wallet is topped up
                                    else:
                                        #  treat as cash and dont deduct from wallet
                                        new_method = 'transfer'
                                        status = 'paid'
                                    wallet.date = selected_match.date
                                    wallet.save()
                                    Payment.objects.create(
                                        user=player.user,
                                        match=selected_match,
                                        amount=cost_per_player,
                                        status=status,
                                        method=new_method,
                                        date=selected_match.date
                                    )
                    return redirect('admin:update_payments')
        else:
            # Just selected the match from the list
            attended_players = Player.objects.filter(
                attendance__match=selected_match, attendance__attended=True
            ).distinct()

    # Show the next 3 upcoming or recent matches
    recent_matches = Match.objects.order_by('-date')[:3]
    # Include wallet balances in the context
    team1_players = [
        {
            'player': player,
            'wallet_balance': Wallet.objects.filter(user=player.user).first().amount if Wallet.objects.filter(user=player.user).exists() else 0
        }
        for player in team1_players
    ]
    team2_players = [
        {
            'player': player,
            'wallet_balance': Wallet.objects.filter(user=player.user).first().amount if Wallet.objects.filter(user=player.user).exists() else 0
        }
        for player in team2_players
    ]
    return render(request, 'admin/update_payments.html', {
        'recent_matches': recent_matches,
        'selected_match': selected_match,
        'team1_players': team1_players,
        'team2_players': team2_players,
    })

@login_required
def create_users(request: HttpRequest):
    if not request.user.is_staff:
        return render(request, 'admin/unauthorized.html', status=403)
    non_staff_users = User.objects.filter(is_staff=False)
    message = None
    if request.method == "POST":
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
    return render(request, 'admin/create_users.html', {'non_staff_users': non_staff_users, 'message': message})

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

def get_urls():
    urls = original_get_urls()
    custom_urls = [
        path('dashboard/', admin.site.admin_view(admin_dashboard), name='admin_dashboard'),
        path('add_users/', admin.site.admin_view(add_users), name='add_users'),
        path('add_user/', admin.site.admin_view(add_user), name='add_user'),
        path('create_match/', admin.site.admin_view(create_match), name='create_match'),
        path('update_payments/', admin.site.admin_view(update_payments), name='update_payments'),
        path('create_users/', admin.site.admin_view(create_users), name='create_users'),
        path('manage_matches/', admin.site.admin_view(manage_matches), name='manage_matches'),
        path('attendance/', admin.site.admin_view(attendance), name='attendance'),
    ]
    return custom_urls + urls

# Reassign the get_urls method
admin.site.get_urls = get_urls

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # ...existing configuration...

    def save_model(self, request, obj, form, change):
        if 'password' in form.cleaned_data:
            password = form.cleaned_data['password']
            # Hash the password only if it is not already hashed.
            if not password.startswith('pbkdf2_sha256$'):
                obj.set_password(password)
        # ...existing code...
        super().save_model(request, obj, form, change)