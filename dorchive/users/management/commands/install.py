import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.apps import apps

class Command(BaseCommand):
    help = 'Installs the project by running migrations, loading fixtures, and creating a superuser.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Starting the installation process..."))

        # Step 1: Create migrations for all apps
        self.stdout.write(self.style.WARNING("Creating migrations..."))
        call_command('makemigrations', interactive=False)
        self.stdout.write(self.style.SUCCESS("Migrations created successfully."))

        # Step 2: Run migrations
        self.stdout.write(self.style.WARNING("Running migrations..."))
        call_command('migrate', interactive=False)
        self.stdout.write(self.style.SUCCESS("Migrations applied successfully."))

        # Step 3: Load fixtures for each app
        self.stdout.write(self.style.WARNING("Loading fixtures..."))
        for app_config in apps.get_app_configs():
            app_fixtures_path = os.path.join(app_config.path, 'fixtures')
            if os.path.exists(app_fixtures_path):
                for fixture in os.listdir(app_fixtures_path):
                    if fixture.endswith('.json'):
                        fixture_path = os.path.join(app_fixtures_path, fixture)
                        self.stdout.write(f"Loading {fixture} for {app_config.label}...")
                        call_command('loaddata', fixture_path)
        self.stdout.write(self.style.SUCCESS("Fixtures loaded successfully."))

        # Step 4: Create default user
        self.stdout.write(self.style.WARNING("Creating default user..."))
        call_command('defaultuser')

        self.stdout.write(self.style.SUCCESS("Installation process completed successfully."))
