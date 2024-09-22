from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.core.files.storage import default_storage
from django.conf import settings
from .models import File, UserStorage


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_userstorage(sender, **kwargs):
    if kwargs["created"]:
        user = kwargs["instance"]
        UserStorage.objects.create(user=user, bytes_total=(1024 * 1024 * 50))
		
@receiver(pre_delete, sender=File)
def file_delete(sender, instance, **kwargs):
    instance.file.delete(False)

@receiver(post_delete, sender=File)
def delete_file_storage(sender, instance, **kwags):
    try:
        path = instance.file.path
        if path:
            default_storage.delete(path)
    except:
        pass
