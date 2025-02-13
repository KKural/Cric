from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse

class User(AbstractUser):
    pass

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')
    date = models.DateField(auto_now_add=True)

class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')
    date = models.DateField(auto_now_add=True)

class Attendance(models.Model):
    player = models.ForeignKey('Player', on_delete=models.CASCADE)  # Changed to Player
    match = models.ForeignKey('Match', on_delete=models.CASCADE)
    attended = models.BooleanField(default=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True)
    class Meta:
        unique_together = [('player', 'match')]

class Match(models.Model):
    name = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.DecimalField(max_digits=10, decimal_places=2)
    team1 = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='team1')
    team2 = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='team2')
    date = models.DateField()
    time = models.TimeField()
    winner = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='winner', null=True)
    location = models.CharField(max_length=100)

    def get_absolute_url(self):
        return reverse('match_detail', args=[self.pk])

class Team(models.Model):
    name = models.CharField(max_length=100)
    captain = models.ForeignKey(User, on_delete=models.CASCADE, related_name='captain')

class Player(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    paid = models.BooleanField(default=False)
    role = models.CharField(max_length=100)
    matches_played = models.PositiveIntegerField(default=0)
    runs_scored = models.PositiveIntegerField(default=0)
    wickets_taken = models.PositiveIntegerField(default=0)
    catches_taken = models.PositiveIntegerField(default=0)
    stumps_taken = models.PositiveIntegerField(default=0)
    class Meta:
        unique_together = [('user', 'team')]