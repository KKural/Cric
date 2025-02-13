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
    
    # Remove debugging breakpoint if not needed:
    # pdb.set_trace()
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
            return redirect('admin:admin_dashboard')
        else:
            message = "All match fields are required."
    return render(request, 'admin/create_match.html', {"message": message, "teams": teams, "users": users})

@staff_member_required
def update_payments(request: HttpRequest):
    selected_match = None
    attended_players = []
    if request.method == 'POST':
        match_id = request.POST.get('match_id')
        if match_id:
            match = get_object_or_404(Match, pk=match_id)
            # If “paid_...” checkboxes are present, process payments
            if any(k.startswith('paid_') for k in request.POST.keys()):
                # Gather the attended players for cost splitting
                attended_player_qs = Player.objects.filter(
                    attendance__match=match, attendance__attended=True
                ).distinct()
                attended_count = attended_player_qs.count()
                if attended_count > 0:
                    cost_per_player = match.cost / attended_count
                    for player in attended_player_qs:
                        if request.POST.get(f'paid_{player.id}', 'off') == 'on':
                            # Deduct from wallet
                            wallet = Wallet.objects.filter(user=player.user).first()
                            if wallet and wallet.amount >= cost_per_player:
                                wallet.amount -= cost_per_player
                                wallet.save()
                            # Mark Payment as paid
                            Payment.objects.update_or_create(
                                user=player.user,
                                date=match.date,
                                defaults={'amount': cost_per_player, 'status': 'paid'},
                            )
                return redirect('admin:update_payments')
            else:
                # Just selected the match from the dropdown
                selected_match = match
                attended_players = Player.objects.filter(
                    attendance__match=match, attendance__attended=True
                ).distinct()

    # Show the next 3 upcoming or recent matches
    recent_matches = Match.objects.order_by('-date')[:3]
    return render(request, 'admin/update_payments.html', {
        'recent_matches': recent_matches,
        'selected_match': selected_match,
        'attended_players': attended_players,
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

def get_urls():
    urls = original_get_urls()
    custom_urls = [
        path('dashboard/', admin.site.admin_view(admin_dashboard), name='admin_dashboard'),
        path('add_users/', admin.site.admin_view(add_users), name='add_users'),
        path('add_user/', admin.site.admin_view(add_user), name='add_user'),
        path('create_match/', admin.site.admin_view(create_match), name='create_match'),
        path('update_payments/', admin.site.admin_view(update_payments), name='update_payments'),
        path('create_users/', admin.site.admin_view(create_users), name='create_users'),
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