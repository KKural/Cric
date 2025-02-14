from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Create the schema 'django_schema' if it does not exist"

    def handle(self, *args, **options):
        schema_name = 'django_schema'
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name};")
        self.stdout.write(self.style.SUCCESS(f"Schema '{schema_name}' ensured."))
