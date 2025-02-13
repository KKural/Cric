import csv
from django.core.management.base import BaseCommand
from indcric.models import User

class Command(BaseCommand):
    help = 'Load initial data from users.csv'

    def handle(self, *args, **kwargs):
        with open('initial_users.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                username = row['username']
                password = row['password']
                email = row['email']
                if not User.objects.filter(username=username).exists():
                    User.objects.create_user(username=username, password=password, email=email)
                    self.stdout.write(self.style.SUCCESS(f'Successfully created user {username}'))
                else:
                    self.stdout.write(self.style.WARNING(f'User {username} already exists'))
