import os
import uuid

from django.contrib import messages
from django.utils.translation import gettext as _

UPLOAD_DIR = 'drive'

class DriveHookset:

    def storage_color(self, user_storage):
        """
        Return labels indicating amount of storage used.
        """
        p = user_storage.percentage
        if p >= 0 and p < 60:
            return "success"
        if p >= 60 and p < 90:
            return "warning"
        if p >= 90 and p <= 100:
            return "danger"
        raise ValueError("percentage out of range")

    def file_created_message(self, request, file):
        messages.success(request, _(f"{file} was created"))

    def file_deleted_message(self, request, file):
        messages.success(request, _(f"{file} has been deleted"))

    def file_updated_message(self, request, file):
        messages.success(request, _(f"{file} has been updated"))

    def file_renamed_message(self, request, file):
        messages.success(request, _(f"File has been renamed to {file}"))

    def file_moved_message(self, request, file):
        messages.success(request, _(f"{file} was moved to {file.parent} "))

    def file_shared_message(self, request, file):
        messages.success(request, _(f"{file} is now shared"))

    def file_unshared_message(self, request, file):
        messages.success(request, _(f"{file} is now unshared"))

    def member_added_message(self, request, group):
        messages.success(request, _(f"New member added"))

    def file_exists_message(self, name, file):
        return f"{name} already exists in {file}"
    
    def folder_pre_delete(self, request, folder):
        for member in folder.get_children():
            if member.__class__ == folder.__class__:
                self.folder_pre_delete(request, member)
            member.delete()
   
    def file_upload_to(self, instance, filename):
        ext = filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        return os.path.join(UPLOAD_DIR, filename)


hookset = DriveHookset()