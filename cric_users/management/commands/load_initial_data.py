import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Load initial user data from initial_users.csv'

    def handle(self, *args, **options):
        User = get_user_model()
        file_path = 'initial_users.csv'  # CSV file in the project root

        try:
            with open(file_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                users_to_create = []
                for row in reader:
                    # Assuming CSV headers: username,password,email,is_staff,is_superuser
                    username = row['username']
                    password = row['password']
                    email = row['email']
                    is_staff = row.get('is_staff', False)  # Default to False if not present
                    is_superuser = row.get('is_superuser', False)  # Default to False if not present

                    user = User(
                        username=username,
                        email=email,
                        is_staff=is_staff,
                        is_superuser=is_superuser
                    )
                    user.set_password(password)  # Hash the password
                    users_to_create.append(user)

                User.objects.bulk_create(users_to_create)
                self.stdout.write(self.style.SUCCESS(f'Created {len(users_to_create)} users'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'CSV file not found: {file_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading data: {e}'))
