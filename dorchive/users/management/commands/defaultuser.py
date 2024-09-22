
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress


class Command(BaseCommand):
    help = "Create default superuser"

    def handle(self, *args, **kwargs):
        email = settings.SUPERUSER_EMAIL
        password = settings.SUPERUSER_PASSWORD

        User = get_user_model()

        if not User.objects.filter(email=email).exists():
            user = User()
            user.email = BaseUserManager.normalize_email(email)
            user.name = "Superuser"
            user.password = make_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            email = EmailAddress(user=user, email=user.email, primary=True, verified=True)
            email.save()
            self.stdout.write(self.style.SUCCESS("Default user created successfully"))
        else:
            self.stdout.write(self.style.ERROR("Default user already created"))