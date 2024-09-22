import itertools
import operator
from django.apps import apps
from django.db.models import Q
from django.db.models.query import QuerySet
from model_utils.managers import SoftDeletableManager


class GroupFileQuerySet(QuerySet):

    def __init__(self, **kwargs):
        if "group" in kwargs:
            self.group = kwargs.pop("group")
        super().__init__(**kwargs)

    def iterator(self):
        shared_model = self.model.group_file_model()
        shared_files = shared_model.for_group(self.group)
        for object in super().iterator():
            if object.pk in shared_files:
                object.shared = True
            yield object


class UserFileQuerySet(QuerySet):

    def __init__(self, **kwargs):
        if "user" in kwargs:
            self.user = kwargs.pop("user")
        super().__init__(**kwargs)

    def iterator(self):
        shared_model = self.model.user_file_model()
        shared_files = shared_model.for_user(self.user)
        for object in super().iterator():
            if object.pk in shared_files:
                object.shared = True
            yield object


class GroupManager(SoftDeletableManager):
    
    def get_all_queryset(self):
        qs = self._queryset_class(model=self.model, using=self._db)
        return qs

    def create_group(self, name, is_public=False):
        drive = self.model(name=name, is_public=is_public)
        drive.save(using=self._db)
        return drive
    
    def files(self, group, **kwargs):  
        direct = kwargs.get("direct", True)    

        File = apps.get_model("drive", "File")
        files = File.objects.for_group(group)

        if direct:
            return files
        for child in files:
            files.extend(self.files(child, **kwargs))
        return files

    def folders(self, group):
        File = apps.get_model("drive", "File")
        return File.objects.filter(group=group).filter(file_type__name="Folder")

    def for_user(self, user):
        try:
            qs = self.filter(
                Q(usergroup__user=user) |
                Q(is_public=True)
            )
            return qs.distinct() & self.distinct()
        except:
            return self.filter(is_public=True) 


class FileManager(SoftDeletableManager):

    def _group_file_queryset(self, group):
        qs = GroupFileQuerySet(model=self.model, using=self._db, group=group)
        return qs.exclude(is_removed=True)
    
    def _user_file_queryset(self, user):
        qs = UserFileQuerySet(model=self.model, using=self._db, user=user)
        return qs.exclude(is_removed=True)

    def _shared_with_group(self, group):
        qs = self._group_file_queryset(group)
        qs = qs.filter(groupfile__group=group).exclude(parent__isnull=False)
        return qs.distinct() & self.distinct()

    def _shared_with_user(self, user):
        qs = self._user_file_queryset(user)
        qs = qs.filter(userfile__user=user).exclude(parent__isnull=False)
        return qs.distinct() & self.distinct()

    def _user_groups_files(self, user):
        group_files = []
        groups = user.usergroups.all()
        if len(groups) > 0:
            for group in groups:
                files = self._shared_with_group(group)
                group_files.extend(files)
        return group_files

    def get_all_queryset(self):
        qs = self._queryset_class(model=self.model, using=self._db)
        return qs
    
    def create_folder(self, name, parent=None, group=None):
        folder = self.model(name=name, parent=parent, group=group)
        folder.save(using=self._db)
        return folder
    
    def children(self, file, **kwargs):
        direct = kwargs.get("direct", True)
        files = self.for_folder(folder=file)
        manager = sorted(files, key=operator.attrgetter("name"))
        if direct:
            return manager
        for child in files:
            manager.extend(self.children(child, **kwargs))
        return manager
    
    def count_children(self, file):
        children = self.children(file, direct=True)
        return len(children)

    def folders_only(self, parent):
        return self.filter(parent=parent).filter(file_type__name="Folder")
    
    def files_only(self, parent):
        return self.filter(parent=parent).exclude(file_type__name="Folder")

    def for_folder(self, folder):
        return self.filter(parent=folder)

    def for_group(self, group):
        """
        Retrieve files that belong to group
        """
        files = self.filter(group=group).exclude(parent__isnull=False)
        return files
    
    def for_person(self, user):
        """
        Retrieve files that belong to user
        """
        files = self.filter(author=user, group__isnull=True, parent__isnull=True)
        return files
   
    def get_shared(self, user):
        """
        Retrieve files that have been shared with user or shared with groups to which user is a member
        """
        user_files = self._shared_with_user(user)
        groups_files = self._user_groups_files(user)

        files = itertools.chain(user_files, groups_files)
        unique_files = {}
        for file in files:
            unique_files[file.name] = file  # Use file name as key to ensure uniqueness
        sorted_files = sorted(unique_files.values(), key=operator.attrgetter("name"))
        return sorted_files

    def get_trash(self, user):
        return self.get_all_queryset().filter(modified_by=user, is_removed=True)

    def get_recent(self, user):
        return self.for_person(user).order_by("-created")[:5]

    def empty_trash(self, user):
        items = self.get_trash(user)
        for item in items:
            item.delete(soft=False)
    
    def restore_trash(self, user):
        return self.get_trash(user).update(is_removed=False)
    
    def restore_files(self, user, files):
        return self.get_trash(user).filter(pk__in=files).update(is_removed=False)


