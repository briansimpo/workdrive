import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DriveConfig(AppConfig):
    name = "dorchive.drive"
    verbose_name = _("Drive")
    namespace = "drive"

    def ready(self):
        with contextlib.suppress(ImportError):
            import dorchive.drive.receivers


APP_NAME = DriveConfig.namespace