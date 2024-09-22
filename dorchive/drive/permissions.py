
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.urls import reverse

from .models import File

class FilePermissionMixin:
   
    def get_permission_required(self):
        """
        Method to define the required permission for accessing the file.
        Override this method in subclasses to customize permissions.
        """
        return 'read'  # Example: 'read', 'write', 'share', 'delete'.
    
    def get_file_tree_url(self, file: File, default="mydrive"):
        if file.has_parent():
            return file.parent.get_absolute_url()
        elif file.has_drive():
            return file.drive.get_absolute_url()
        else:
            return reverse(default)

    def get_object(self, queryset=None):
        """
        Override the get_object method to check file permissions.
        """
        # Get the file object based on the URL parameter (assumes 'pk' is used in URL)
        queryset = self.get_queryset() if queryset is None else queryset
        pk = self.kwargs.get('pk')
        file = get_object_or_404(queryset, pk=pk)

        # Perform permission check based on the defined `get_permission_required()` method
        permission_required = self.get_permission_required()
        if not self.has_permission(file, permission_required):
            raise Http404("You do not have permission to access this file.")

        return file

    def has_permission(self, file, permission):
        user = self.request.user
        return user.has_file_permission(file, permission)

class FileReadPermission(FilePermissionMixin):
    def get_permission_required(self):
        return 'read'
 
class FileWritePermission(FilePermissionMixin):

    def get_permission_required(self):
        return 'write'

class FileSharePermission(FilePermissionMixin):
    
    def get_permission_required(self):
        return 'share'
    
class FileDeletePermission(FilePermissionMixin):

    def get_permission_required(self):
        return 'delete'

class GroupAdminPermission:
   
    def get_object(self, queryset=None):
        """
        Override the get_object method to check file permissions.
        """
        # Get the file object based on the URL parameter (assumes 'pk' is used in URL)
        queryset = self.get_queryset() if queryset is None else queryset
        pk = self.kwargs.get('pk')
        group = get_object_or_404(queryset, pk=pk)
        user = self.request.user

        if not group.is_public and user.is_group_admin(group):
            raise Http404("You do not have permission as group admin.")
        return group

class GroupMemberPermission:
   
    def get_object(self, queryset=None):
        """
        Override the get_object method to check file permissions.
        """
        # Get the file object based on the URL parameter (assumes 'pk' is used in URL)
        queryset = self.get_queryset() if queryset is None else queryset
        pk = self.kwargs.get('pk')
        group = get_object_or_404(queryset, pk=pk)

        user = self.request.user
        if not group.is_public and not user.is_group_member(group):
            raise Http404("You do not have permission as group member.")
        return group
