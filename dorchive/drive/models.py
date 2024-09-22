import itertools
import math
from django.db import models
from django.db.models import F
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from model_utils.models import TimeStampedModel, UUIDModel, SoftDeletableModel

from .utils import convert_bytes
from .exceptions import DuplicateFileError
from .managers import FileManager, GroupManager
from .hooks import hookset


def uuid_filename(instance, filename):
    return hookset.file_upload_to(instance, filename)

class FileType(UUIDModel):
    name = models.CharField(max_length=140)
    icon = models.CharField(max_length=255, default=None, blank=True, null=True)
    extension = models.CharField(max_length=140, default=None, blank=True, null=True)

    def __str__(self):
        if self.extension:
            return f"{self.name}({self.extension})"
        else:
            return self.name
    
    @classmethod
    def get_by_name(cls, name):
        object = cls.objects.filter(name=name).first()
        if not object:
            object = FileType.get_file()
        return object
    
    @classmethod
    def get_folder(cls):
        return FileType.get_by_name("Folder")
    
    @classmethod
    def get_file(cls):
        return FileType.get_by_name("File")

    @classmethod
    def get_by_extension(cls, extension):
        object = cls.objects.filter(extension=extension).first()
        if not object:
            object = FileType.get_file()
        return object


class Group(UUIDModel, TimeStampedModel, SoftDeletableModel):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        through='UserGroup', 
        related_name='group_members'
    )

    files = models.ManyToManyField(
        "drive.File", 
        through='GroupFile', 
        related_name="group_files",
        blank=True
    )

    objects = GroupManager()

    @staticmethod
    def get_files(group):
        return Group.objects.files(group)
    
    @staticmethod
    def get_folders(group):
        return Group.objects.folders(group)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("group", kwargs={"pk": self.pk})

    def get_members_url(self):
        return reverse("group_members", kwargs={"pk": self.pk})
    
    def get_remove_member_url(self):
        return reverse("remove_member", kwargs={"pk": self.pk})
    
    def get_admin_url(self):
        return reverse("group_admin", kwargs={"pk": self.pk})

    def is_group_member(self, member):
        return (self.users.filter(usergroup__user=member).exists())

    def get_members(self):
        return UserGroup.objects.filter(group=self)
    
    def get_non_members(self):
        qs = self.users.all()
        User = get_user_model()
        if qs.exists():
            return User.objects.exclude(pk__in=qs.values("id"))
        return User.objects.all()
    
    def get_absolute_url(self):
        return reverse("group", kwargs={"pk": self.pk})
    
    def add_member(self, member):
        if not self.is_group_member(member):
            user_group = UserGroup(user=member, group=self)
            user_group.save()

    def remove_member(self, member):
        if self.is_group_member(member):
            UserGroup.objects.filter(user=member, group=self).delete()

    def add_members(self, members):
        for member in members:
            self.add_member(member)

    def remove_members(self, members):
        for member in members:
            self.remove_member(member)

    def set_admin(self, member, is_admin=True):
        object = UserGroup.objects.filter(group=self, user=member).first()
        object.is_admin = is_admin
        object.save()


class FileNavigation(models.Model):
    class Meta:
        abstract = True
    
    def get_absolute_url(self):
        return reverse("file_view", kwargs={"pk": self.pk})
    
    def get_info_url(self):
        return reverse("file_info", kwargs={"pk": self.pk})
    
    def get_update_url(self):
        return reverse("file_update", kwargs={"pk": self.pk})
    
    def get_download_url(self):
        return reverse("file_download", kwargs={"pk": self.pk})

    def get_rename_url(self):
        return reverse("file_rename", kwargs={"pk": self.pk})
    
    def get_organize_url(self):
        return reverse("file_organize", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("file_delete", kwargs={"pk": self.pk})

    def get_share_group_url(self):
        return reverse("file_share_group", kwargs={"pk": self.pk})
    
    def get_share_people_url(self):
        return reverse("file_share_people", kwargs={"pk": self.pk})
    
    def get_remove_group_url(self):
        return reverse("file_remove_group", kwargs={"pk": self.pk})
    
    def get_remove_people_url(self):
        return reverse("file_remove_people", kwargs={"pk": self.pk})
    
    def get_shared_file_url(self):
        return reverse("shared_file", kwargs={"pk": self.pk})
    
    def get_remove_file_url(self):
        return reverse("remove_file", kwargs={"pk": self.pk})
    
    def get_restore_file_url(self):
        return reverse("restore_file", kwargs={"pk": self.pk})


class FilePermission(models.Model):
    can_read = models.BooleanField(default=True)
    can_write = models.BooleanField(default=True)
    can_delete = models.BooleanField(default=False)

    class Meta:
        abstract = True

    @property
    def access(self):
        read = "R" if self.can_read else ""
        write = "W" if self.can_read else ""
        delete = "D" if self.can_delete else ""
        return "{}{}{}".format(read, write, delete)
    
    def set_permissions(self, permissions:dict):
        self.can_read = permissions.get("can_read", True)
        self.can_write = permissions.get("can_write", True)
        self.can_delete = permissions.get("can_delete", False)

    def get_permissions(self):
        return {
            "can_read": self.can_read,
            "can_write": self.can_write,
            "can_delete": self.can_delete
        }

    def cascade_permission(self):
        if self.is_folder:
            children = self.get_children(direct=False)
            for child in children:
                child.set_permissions(self.get_permissions())
                child.save()


class FileSharing(models.Model):
    shared = None
    class Meta:
        abstract = True

    @classmethod
    def group_file_model(cls):
        return GroupFile
    
    @classmethod
    def user_file_model(cls):
        return UserFile

    def is_shared(self):
        return (
            self.groupfile_set.filter(folder=self).exists() or 
            self.userfile_set.filter(folder=self).exists()
        )

    def is_shared_with_group(self, group):
        return (self.groupfile_set.filter(group=group).exists())
    
    def is_shared_with_person(self, user):
        return (self.userfile_set.filter(user=user).exists())
    
    def is_shared_with_groups(self):
        return (self.groupfile_set.filter(file=self).exists())
    
    def is_shared_with_people(self):
        return (self.userfile_set.filter(file=self).exists())

    def get_shared_parent(self):
        root = self
        a, b = itertools.tee(reversed(self.get_ancestors()))
        next(b, None)
        for file, parent in itertools.zip_longest(a, b):
            if file.shared:
                root = file
            if parent is None or not parent.shared:
                break
        return root

    def get_shared_groups(self):
        qs = self.groupfile_set.filter(file=self)
        if qs.exists():
            return Group.objects.filter(pk__in=qs.values("groupfile__group"))
        return Group.objects.none()
    
    def get_shared_people(self):
        qs = self.userfile_set.filter(file=self)
        User = get_user_model()
        if qs.exists():
            return User.objects.filter(pk__in=qs.values("user"))
        return User.objects.none()
    
    def get_file_groups(self, **kwargs):
        user = kwargs.pop("user", None)
        if user is not None:
            return self.groupfile_set.filter(file=self, shared_by=user)
        return self.groupfile_set.filter(file=self)
        
    def get_file_users(self, **kwargs):
        user = kwargs.pop("user", None)
        if user is not None:
            return self.userfile_set.filter(file=self, shared_by=user)
        return self.userfile_set.filter(file=self)
    
    def get_non_shared_groups(self):
        qs = self.groupfile_set.filter(file=self)
        if qs.exists():
            return Group.objects.exclude(pk__in=qs.values("group"))
        return Group.objects.all()
        
    def get_non_shared_people(self):
        qs = self.userfile_set.filter(file=self)
        User = get_user_model()
        if qs.exists():
            return User.objects.exclude(pk__in=qs.values("user"))
        return User.objects.all()

    def add_group(self, group, **kwargs):
        permissions = kwargs.pop("permissions")
        user = kwargs.pop("user", None)
        if not self.is_shared_with_group(group):
            files = [self] + self.get_children(direct=False)
            for file in  files:
                object = GroupFile(file=file, group=group)
                object.set_permissions(permissions)
                object.touch(user=user, commit=True)

    def add_groups(self, groups, **kwargs):
        for group in groups:
            self.add_group(group, **kwargs)

    def add_person(self, person, **kwargs):
        permissions = kwargs.pop("permissions")
        shared_by = kwargs.pop("shared_by", None)
        files = [self] + self.get_children(direct=False)
        for file in files:
            if not file.is_shared_with_person(person):
                object = UserFile(file=file, user=person)
                object.set_permissions(permissions)
                object.touch(shared_by=shared_by, commit=True)

    def add_people(self, users, **kwargs):
        for person in users:
            self.add_person(person, **kwargs)

    def remove_group(self, group):
        files = [self] + self.get_children(direct=False)
        for file in files:
            if file.is_shared_with_group(group):
                GroupFile.objects.filter(file=file, group=group).delete()

    def remove_groups(self, groups):
        for group in groups:
           self.remove_group(group)

    def remove_person(self, user):
        files = [self] + self.get_children(direct=False)
        for file in files:
            if file.is_shared_with_person(user):
                UserFile.objects.filter(file=file, user=user).delete()

    def remove_people(self, users):
       for user in users:
           self.remove_person(user)
    
    def _shared_group_permissions(self, group):
        file = GroupFile.objects.filter(group=group, file=self.parent).first()
        return {
            "permissions" : file.get_permissions(),
            "shared_by": file.shared_by
        }

    def _shared_user_permissions(self, user):
        file = UserFile.objects.filter(user=user, file=self.parent).first()
        return {
            "permissions" : file.get_permissions(),
            "shared_by": file.shared_by
        }

    def _cascade_groups_share(self):
        groups = self.parent.get_shared_groups()
        for group in groups:
            kwargs = self._shared_group_permissions(group)
            self.add_group(group, **kwargs)

    def _cascade_people_share(self):
        people = self.parent.get_shared_people()
        for user in people:
            kwargs = self._shared_user_permissions(user)
            self.add_person(user, **kwargs)

    def cascade_share(self):
        if self.has_parent():
            if self.parent.is_shared_with_groups():
                self._cascade_groups_share()
            if self.parent.is_shared_with_people():
                self._cascade_people_share()


class FileTypeGuessor(models.Model):
    file_type = models.ForeignKey(FileType,  on_delete=models.CASCADE, blank=True, null=True)
    class Meta:
        abstract = True

    @property
    def icon(self):
        if self.file_type:
            return self.file_type.icon
    
    def is_docs(self):
        return str(self.file_type.name).lower() == "docs"
    
    def is_sheets(self):
        return str(self.file_type.name).lower() == "sheets"
    
    def is_slides(self):
        return str(self.file_type.name).lower() == "slides"
    
    def is_pdf(self):
        return str(self.file_type.name).lower() == "pdf"
    
    def is_text(self):
        return str(self.file_type.name).lower() == "text"
    
    def is_picture(self):
        return str(self.file_type.name).lower() == "picture"
    
    def is_audio(self):
        return str(self.file_type.name).lower() == "audio"
    
    def is_video(self):
        return str(self.file_type.name).lower() == "video"
    
    def is_zip(self):
        return str(self.file_type.name).lower() == "zip"


class File(UUIDModel, FileTypeGuessor, FileSharing, FilePermission, FileNavigation, TimeStampedModel, SoftDeletableModel):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)
    file = models.FileField(upload_to=uuid_filename, blank=True, null=True)
    original_filename = models.CharField(max_length=500, blank=True, null=True)
    published = models.BooleanField(default=False)
    parent = models.ForeignKey(
        'self', 
        related_name="file_parent", 
        on_delete=models.CASCADE, 
        blank=True, null=True
    )
    group = models.ForeignKey(
        Group, 
        related_name="file_group", 
        on_delete=models.CASCADE, 
        blank=True, null=True
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name="file_author", 
        on_delete=models.CASCADE
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name="file_modifier", 
        on_delete=models.CASCADE
    )
    
    objects = FileManager()

    @classmethod
    def already_exists(cls, name, parent, group):
        return cls.objects.filter(name=name,parent=parent,group=group).exists()

    @property
    def size(self):
        return self.get_size()
    
    @property
    def bytes(self):
        return self.get_bytes()

    @property
    def owner(self):
        if self.group:
            return self.group
        else:
            return self.author

    @property
    def status(self):
        return self.published

    def __str__(self):
        return self.name

    def __set_as_file(self):
        split_file = str(self.file).split(".")
        extension = split_file[1]
        file_type = FileType.get_by_extension(extension)
        self.file_type = file_type

    def __set_as_folder(self):
        file_type = FileType.get_folder()
        self.file_type = file_type

    def is_folder(self):
        return self.original_filename is None

    def is_file(self):
        return self.original_filename is not None

    def is_root(self):
        return self.parent is None

    def get_size(self):
        if self.file:
            return self.file.size
        else:
            children = self.get_children(direct=True)
            return sum([member.size for member in children ])
        
    def get_bytes(self):
        size = self.get_size()
        if size is not None:
            return convert_bytes(size)

    def get_children(self, **kwargs):
        return File.objects.children(file=self, **kwargs)
    
    def count_children(self):
        return File.objects.count_children(file=self, direct=True)
    
    def has_children(self):
        count = self.count_children()
        return count > 0

    def get_ancestors(self):
        ancestors = []
        if self.parent:
            ancestors.extend(self.parent.get_ancestors())
            ancestors.append(self.parent)
        return ancestors

    def has_ancestors(self):
        return len(self.get_ancestors()) > 0
    
    def is_duplicate(self):
        return File.already_exists(self.name, self.parent, self.drive)

    def has_parent(self):
        return self.parent is not None

    def has_group(self):
        return self.group is not None

    def touch(self, user, commit=True):
        self.modified_by = user
        if commit:
            if self.parent:
                self.parent.touch(user)
            self.save()

    def move(self, destination):
        self.parent = destination
        self.save()

    def save(self, **kwargs):
        if not self.pk and self.is_duplicate():
            raise DuplicateFileError(f"{self.name} already exists.")
        if self.is_folder():
            self.__set_as_folder()
        else:
            self.__set_as_file()
        
        self.touch(self.author, commit=False)
        super().save(**kwargs)

    def unique_id(self):
        return "f-%d" % self.pk
    
    def permanent_delete(self):
        self.delete(soft=False)

    def restore(self):
        self.is_removed = False
        self.save()

    @staticmethod
    def for_person(user):
        return File.objects.for_person(user)
    
    @staticmethod
    def get_files(folder):
        return File.objects.children(folder)
    
    @staticmethod
    def get_shared(user):
        return File.objects.get_shared(user)

    @staticmethod    
    def get_recent(user):
        return File.objects.get_recent(user)

    @staticmethod    
    def get_trash(user):
        return File.objects.get_trash(user)


class Folder(File):
    class Meta:
        proxy = True


class Document(File):
    class Meta:
        proxy = True

    @classmethod
    def already_exists(cls, name, parent, author):
        return cls.objects.filter(name=name,parent=parent,author=author).exists()
    
    def is_duplicate(self):
        return Document.already_exists(self.name, self.parent, self.author)


class ShareFile(FilePermission, UUIDModel, TimeStampedModel):
    file = models.ForeignKey(File, on_delete=models.CASCADE)
    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name="+", 
        on_delete=models.CASCADE,
        blank=True, null=True
    )

    obj_attr = "file"
    class Meta:
        abstract = True

    def touch(self, shared_by, commit=True):
        self.shared_by = shared_by
        if commit:
            self.save()

    def save(self, **kwargs):
        self.touch(self.shared_by, commit=False)
        super().save(**kwargs)


class GroupFile(ShareFile):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    class Meta:
        unique_together = [("group", "file")]

    @classmethod
    def for_group(cls, group):
        qs = cls._default_manager.filter(group=group)
        return qs.values_list(cls.obj_attr)


class UserFile(ShareFile):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name="+", 
        on_delete=models.CASCADE
    )
    class Meta:
        unique_together = [("user", "file")]

    @classmethod
    def for_user(cls, user):
        qs = cls._default_manager.filter(user=user)
        return qs.values_list(cls.obj_attr)


class UserGroup(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)

    class Meta:
        unique_together = [("user", "group")]

    def __str__(self) -> str:
        return self.group.name


class UserStorage(UUIDModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="storage", on_delete=models.CASCADE)
    bytes_used = models.BigIntegerField(default=0)
    bytes_total = models.BigIntegerField(default=0)

    @property
    def percentage(self):
        return int(math.ceil((float(self.bytes_used) / self.bytes_total) * 100))

    @property
    def color(self):
        return hookset.storage_color(self)
    
    def increase_usage(self, bytes):
        storage_qs = UserStorage.objects.filter(pk=self.pk)
        storage_qs.update(bytes_used=F("bytes_used") + bytes)

    def reduce_usage(self, bytes):
        storage_qs = UserStorage.objects.filter(pk=self.pk)
        storage_qs.update(bytes_used=F("bytes_used") - bytes)


class DriveMixin(models.Model):

    usergroups = models.ManyToManyField(
        Group,
        through='drive.UserGroup', 
        through_fields=["user", "group"],
        related_name="users_groups",
        related_query_name="user",
        blank=True
    )

    userfiles = models.ManyToManyField(
        File, 
        through='drive.UserFile', 
        through_fields=["user", "file"],
        related_name="users_files",
        related_query_name="user",
        blank=True
    )

    class Meta:
        abstract = True
  
    def _has_direct_permission(self, file, permission):
        try:
            action_name = "can_%s" % permission
            if file.group and self.is_group_member(file.group) and getattr(file, action_name) == True:
                return True
            return False
        except:
            return False

    def _has_user_file_permission(self, file, permission):
        try: 
            action_name = "can_%s" % permission
            user_file = UserFile.objects.filter(file=file, user=self).first()
            if user_file and getattr(user_file, action_name) == True:
                return True
            return False
        except:
            return False
       
    def _has_group_file_permission(self, file, permission):
        action_name = "can_%s" % permission
        try:
            groups = self.usergroups.all()
            group_file = GroupFile.objects.filter(file=file, group__in=groups).first()
            if group_file and getattr(group_file, action_name) == True:
                return True
            return False
        except:
            return False
        
    def get_groups(self):
        groups = Group.objects.for_user(user=self) 
        return groups
   
    def is_group_admin(self, group):
        return UserGroup.objects.filter(group=group, user=self, is_admin=True).exists()
    
    def is_group_member(self, group):
        return UserGroup.objects.filter(group=group, user=self).exists()

    def is_file_author(self, file):
        return file.author.pk == self.pk
    
    def is_file_admin(self, file):
        if file.group and self.is_group_admin(file.group):
            return True
        return False
   
    def has_file_permission(self, file, permission):

        if self._has_direct_permission(file, permission):
            return True
    
        if self.is_file_author(file):
            return True
        
        if self.is_file_admin(file):
            return True
        
        if self._has_user_file_permission(file, permission):
            return True
        
        if self._has_group_file_permission(file, permission):
            return True
        
        return False

    def can_access(self, file):
        return (
            self.can_read(file) or 
            self.can_write(file) or 
            self.can_delete(file)
        )

    def can_read(self, file):
        return self.has_file_permission(file, "read")
    
    def can_write(self, file):
        return self.has_file_permission(file, "write")
    
    def can_delete(self, file):
        return self.has_file_permission(file, "delete")

