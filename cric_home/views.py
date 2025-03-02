from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from cric_users.models import Match
from django.utils import timezone

@login_required
def home_view(request):
    upcoming_matches = Match.objects.filter(date__gte=timezone.now().date()).order_by('date', 'time')
    previous_matches = Match.objects.filter(date__lt=timezone.now().date()).order_by('-date', '-time')
    context = {
        'upcoming_matches': upcoming_matches,
        'previous_matches': previous_matches,
    }
    return render(request, "home.html", context)

@login_required
def match_detail_view(request, match_id):
    match = get_object_or_404(Match, pk=match_id)
    teams = match.team_set.all()  # each match has exactly 2 teams
    if teams.count() >= 2:
        team1 = teams[0]
        team2 = teams[1]
        team1_players = team1.player_set.select_related('user').all()
        team2_players = team2.player_set.select_related('user').all()
    else:
        team1 = team2 = None
        team1_players = team2_players = []
    context = {
        'match': match,
        'team1': team1,
        'team2': team2,
        'team1_players': team1_players,
        'team2_players': team2_players,
    }
    return render(request, 'cric_home/match_detail.html', context)