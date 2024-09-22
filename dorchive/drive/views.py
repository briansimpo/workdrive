from django.db import transaction
from django.db.models import F
from django.forms import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import static
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    TemplateView,
    UpdateView
)
from django.views.generic.detail import (
    SingleObjectMixin,
    SingleObjectTemplateResponseMixin,
)
from django.views.generic.edit import FormMixin, ProcessFormView
from django.views.generic import FormView
from django.conf import settings
from dorchive.utils.helpers import get_template_name
from dorchive.users.mixins import UserMixin
from .permissions import (
    FileDeletePermission,
    FileReadPermission,
    FileSharePermission,
    FileWritePermission,
    GroupAdminPermission,
    GroupMemberPermission
)
from .forms import (
    FileUpdateForm,
    FileUploadForm,
    FolderCreateForm,
    FileOrganizeForm,
    FileRenameForm,
    ShareWithGroupForm,
    ShareWithPeopleForm,
    GroupMemberForm,
)
from .hooks import hookset
from .models import Document, File, Folder, Group
from .apps import DriveConfig

APP_NAME = DriveConfig.namespace

HOME_URL = "home"
MY_DRIVE_URL = "mydrive"
TRASH_URL = "trash"

class Index(UserMixin, TemplateView):
    template_name =  get_template_name("home.html", APP_NAME)

class MyDrive(UserMixin, TemplateView):
    template_name =  get_template_name("mydrive/index.html", APP_NAME)
    model = File
    context_object_name = "file"

    def get_files(self, user):
        return File.for_person(user)
    
    def create_folder_form(self):
        return FolderCreateForm()
    
    def upload_file_form(self):
        return FileUploadForm()
    
    def get_context_data(self, **kwargs):
        context = kwargs
        user = self.get_user()
        files = self.get_files(user)
        create_folder_form = self.create_folder_form()
        upload_file_form = self.upload_file_form()
        context.update({ 
            "create_folder_form": create_folder_form,
            "upload_file_form": upload_file_form,
            "files": files,
        })
        return context

class GroupView(UserMixin, GroupMemberPermission, DetailView):
    template_name =  get_template_name("group/index.html", APP_NAME)
    model = Group

    def folder_create_form(self, group: Group):
        parent = None
        return FolderCreateForm(initial={
            "group":group,
            "parent": parent
        })
    
    def upload_file_form(self, group: Group, **kwargs):
        parent = None
        return FileUploadForm(initial={
            "group": group,
            "parent": parent
        })
    
    def get_files(self, group: Group):
        return Group.get_files(group)

    def get_context_data(self, **kwargs):
        context = kwargs
        group = self.get_object()
        create_folder_form = self.folder_create_form(group)
        upload_file_form = self.upload_file_form(group)
        files = self.get_files(group)
        context.update({ 
            "group": group,
            "create_folder_form": create_folder_form,
            "upload_file_form": upload_file_form,
            "files": files,
        })
        return context
    
class GroupMembersView(UserMixin, SingleObjectTemplateResponseMixin,FormMixin,SingleObjectMixin, GroupAdminPermission, ProcessFormView):
    template_name =  get_template_name("group/members.html", APP_NAME)
    model = Group
    form_class = GroupMemberForm
    context_object_name = "group"

    def get_group_members(self, group: Group):
        return group.get_members()
    
    def get_form_kwargs(self):
        object = self.get_object()
        kwargs = super().get_form_kwargs()
        non_members = object.get_non_members()
        kwargs.update({"members": non_members})
        return kwargs

    def get_context_data(self, **kwargs):
        context = kwargs
        object = self.get_object()
        member_form = self.get_form()
        group_members = self.get_group_members(object)

        context.update({
            "group": object,
            "member_form": member_form,
            "group_members": group_members,
        })
        return context

    def form_valid(self, form):
        object = self.get_object()
        members = form.cleaned_data["members"]
        object.add_members(members)

        hookset.member_added_message(self.request, object)
        return redirect(object.get_members_url())

class GroupRemoveMember(UserMixin, GroupAdminPermission, DetailView):
    model = Group

    def post(self, request, *args, **kwargs):
        object = self.get_object()
        members = []
        members.append(request.POST.get("member"))
        object.remove_members(members)
        return redirect(object.get_members_url())

class GroupAdmin(UserMixin, GroupAdminPermission, DetailView):
    model = Group

    def post(self, request, *args, **kwargs):
        object = self.get_object()
        member = request.POST.get("member")
        is_admin = bool(request.POST.get("is_admin"))
        object.set_admin(member, is_admin)
        return redirect(object.get_members_url())

class FileView(UserMixin, FileReadPermission, DetailView):
    template_name =  get_template_name("files/index.html", APP_NAME)
    model = File
    context_object_name = "file"

    def create_folder_form(self, parent:File, **kwargs):
        return FolderCreateForm(initial={
            "group":parent.group,
            "parent": parent
        })
    
    def upload_file_form(self, parent: File, **kwargs):
        return FileUploadForm(initial={
            "group":parent.group,
            "parent": parent
        })
    
    def rename_file_form(self, file: File, **kwargs):
        return FileRenameForm(instance=file)
    
    def organize_file_form(self, file:File, **kwargs):
        group = file.group
        folders = Group.get_folders(group)
        kwargs.update({"folders" : folders})
        return FileOrganizeForm(instance=file, **kwargs)
    
    def update_file_form(self, file: File, **kwargs):
        return FileUpdateForm(instance=file)
    
    def share_group_form(self, file: File, **kwargs):
        non_shared_groups = file.get_non_shared_groups()
        return ShareWithGroupForm(groups = non_shared_groups)
    
    def share_people_form(self, file: File, **kwargs):
        non_shared_people = file.get_non_shared_people()
        return ShareWithPeopleForm(people = non_shared_people)

    def get_shared_groups(self, file: File):
        user = self.get_user()
        return file.get_file_groups(user=user)
    
    def get_shared_people(self, file: File):
        user = self.get_user()
        return file.get_file_users(user=user)
    
    def get_files(self, file:File, **kwargs):
        return File.get_files(file)

    def get_context_data(self, **kwargs):
        context = kwargs
        file = self.get_object()
        create_folder_form = self.create_folder_form(parent=file)
        upload_file_form = self.upload_file_form(parent=file)
        rename_file_form = self.rename_file_form(file=file)
        organize_file_form = self.organize_file_form(file=file)
        update_file_form = self.update_file_form(file=file)
        share_group_form = self.share_group_form(file=file)
        share_people_form = self.share_people_form(file=file)

        files = self.get_files(file=file)
        shared_groups = self.get_shared_groups(file=file)
        shared_people = self.get_shared_people(file=file)
        context.update({ 
            "file": file,
            "files": files,
            "shared_groups": shared_groups,
            "shared_people": shared_people,
            "create_folder_form": create_folder_form,
            "upload_file_form": upload_file_form,
            "rename_file_form": rename_file_form,
            "organize_file_form": organize_file_form,
            "update_file_form": update_file_form,
            "share_group_form": share_group_form,
            "share_people_form": share_people_form

        })
        return context

class TrashView(UserMixin, TemplateView):
    template_name =  get_template_name("trash/index.html", APP_NAME)

    def get_files(self, user):
        return File.get_trash(user)
    
    def get_context_data(self, **kwargs):
        context = kwargs
        user = self.get_user()
        files = self.get_files(user)
        context.update({ 
            "files": files
        })
        return context
    
class RecentView(UserMixin, TemplateView):
    template_name =  get_template_name("recent/index.html", APP_NAME)

    def get_files(self, user):
        return File.get_recent(user)
    
    def get_context_data(self, **kwargs):
        context = kwargs
        user = self.get_user()
        files = self.get_files(user)
        context.update({ 
            "files": files
        })
        return context

class SharedView(UserMixin, TemplateView):
    template_name =  get_template_name("shared/index.html", APP_NAME)

    def get_files(self, user):
        return File.get_shared(user)
    
    def get_context_data(self, **kwargs):
        context = kwargs
        user = self.get_user()
        files = self.get_files(user)
        context.update({ 
            "files": files
        })
        return context

class SharedFile(FileView):
    template_name =  get_template_name("shared/detail.html", APP_NAME)

class FolderCreate(UserMixin, FileWritePermission, FormView):
    template_name =  get_template_name("files/create_folder.html", APP_NAME)
    model = Folder
    form_class = FolderCreateForm

    def get_data(self, form, **kwargs):
        name = form.cleaned_data["name"]
        parent = form.cleaned_data["parent"]
        group = form.cleaned_data["group"]
        author = self.get_user()

        kwargs.update({
            "name": name,
            "group": group,
            "parent": parent,
            "author": author
        })
        return kwargs

    def create(self, **kwargs):
        user = self.get_user()
        folder = self.model.objects.create(**kwargs)
        folder.touch(user)
        folder.cascade_permission()
        folder.cascade_share()
        return folder
    
    def validate(self, **kwargs):
        name = kwargs.get("name")
        parent = kwargs.get("parent")
        group = kwargs.get("group")

        if Folder.already_exists(name, parent, group):
            raise ValidationError(f"{name} already exists.")

    def form_valid(self, form):
        kwargs = self.get_data(form)
        success_url = None
        self.validate(**kwargs)
        object = self.create(**kwargs)
        if object.parent:
            success_url = object.parent.get_absolute_url()
        elif object.group:
            success_url = object.group.get_absolute_url()
        else:
            success_url = reverse(MY_DRIVE_URL)

        hookset.file_created_message(self.request, object)
        return redirect(success_url)

class FileUpdate(UserMixin, FileReadPermission, FileWritePermission, UpdateView):
    template_name =  get_template_name("files/update.html", APP_NAME)
    model = File
    form_class = FileUpdateForm
    context_object_name = "file"

    def form_valid(self, form):
        super().form_valid(form)
        object = self.get_object()
        hookset.file_updated_message(self.request, object)
        return redirect(object.get_absolute_url())

class FileInfo(UserMixin, FileReadPermission, DetailView):
    template_name =  get_template_name("files/info.html", APP_NAME)
    model = File
    context_object_name = "file"

class FileUpload(UserMixin, FileWritePermission, CreateView):
    template_name =  get_template_name("files/upload.html", APP_NAME)
    model = Document
    form_class = FileUploadForm
    
    def create(self, **kwargs):
        user = self.get_user()
        document = self.model.objects.create(**kwargs)
        document.touch(user)
        document.cascade_share()
        return document

    def get_data(self, file, parent, group):
        return {
            "name": file.name,
            "original_filename": file.name,
            "parent": parent,
            "group" : group,
            "author": self.request.user,
            "file": file,
        }
    
    def get_success_url(self) -> str:
        if self.object.parent:
            return self.object.parent.get_absolute_url()
        elif self.object.group:
            return self.object.group.get_absolute_url()
        else:
            return self.object.get_absolute_url()

    def form_valid(self, form):
        with transaction.atomic():
            files = form.cleaned_data["file"]
            parent = form.cleaned_data["parent"]
            group = form.cleaned_data["group"]
            author = self.request.user

            for file in files:
                name = file.name
                if Document.already_exists(name, parent, author):
                    raise ValidationError(hookset.file_exists_message(name, parent))
                kwargs = self.get_data(file, parent, group)
                self.object = self.create(**kwargs)
            return redirect(self.get_success_url())

class FileDownload(UserMixin, FileReadPermission, DetailView):
    model = File
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if settings.DEBUG is False:
            response = HttpResponse()
            response["X-Accel-Redirect"] = self.object.file.url
            del response["content-type"]
        else:
            response = static.serve(request, self.object.file.name,document_root=settings.MEDIA_ROOT)
        return response

class FileRename(UserMixin, FileWritePermission, UpdateView):
    template_name =  get_template_name("files/rename.html", APP_NAME)
    model = File
    form_class = FileRenameForm
    context_object_name = "file"

    def form_valid(self, form):
        super().form_valid(form)
        object = self.get_object()
        hookset.file_renamed_message(self.request, object)
        return redirect(object.get_absolute_url())

class FileOrganize(UserMixin, FileWritePermission, UpdateView):
    template_name =  get_template_name("files/organize.html", APP_NAME)
    model = File
    form_class = FileOrganizeForm
    context_object_name = "file"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        group = self.object.group
        folders = Group.get_folders(group)
        kwargs.update({"folders": folders})
        return kwargs
    
    def form_valid(self, form):
        object = self.get_object()
        parent = form.cleaned_data["parent"]
        object.move(parent)
        hookset.file_moved_message(self.request, object)
        return redirect(object.get_absolute_url())
 
class FileDelete(UserMixin, FileDeletePermission, DeleteView):
    template_name =  get_template_name("files/delete.html", APP_NAME)
    model = File
    context_object_name = "file"

    def post(self, request, *args, **kwargs):
        object = self.get_object()
        success_url = None
        if object.parent:
            success_url = object.parent.get_absolute_url()
        elif object.group:
            success_url = object.group.get_absolute_url()
        else:
            success_url = reverse(MY_DRIVE_URL)

        object.delete()
        hookset.file_deleted_message(request, object)
        return redirect(success_url)

class FileShareWithGroup(UserMixin, SingleObjectTemplateResponseMixin,FormMixin,SingleObjectMixin, FileSharePermission, ProcessFormView):
    template_name =  get_template_name("files/share_group.html", APP_NAME)
    model = File
    form_class = ShareWithGroupForm
    context_object_name = "file"

    def get_shared_groups(self, file: File):
        user = self.get_user()
        return file.get_file_groups(user=user)
    
    def get_form_kwargs(self):
        object = self.get_object()
        kwargs = super().get_form_kwargs()
        non_shared_groups = object.get_non_shared_groups()
        kwargs.update({"groups": non_shared_groups})
        return kwargs

    def get_context_data(self, **kwargs):
        context = kwargs
        object = self.get_object()
        share_group_form = self.get_form()
        shared_groups = self.get_shared_groups(object)

        context.update({
            "file": object,
            "share_group_form": share_group_form,
            "shared_groups": shared_groups,
        })
        return context

    def form_valid(self, form):
        user = self.get_user()
        object = self.get_object()
        groups = form.cleaned_data["groups"]

        permissions = {
            "can_read" : form.cleaned_data["can_read"],
            "can_write": form.cleaned_data["can_write"],
            "can_delete": form.cleaned_data["can_delete"],
        }
        kwargs = {
            "permissions" : permissions,
            "shared_by": user
        }

        object.add_groups(groups, **kwargs)

        hookset.file_shared_message(self.request, object)
        return redirect(object.get_absolute_url())

class FileShareWithPeople(UserMixin, SingleObjectTemplateResponseMixin,FormMixin,SingleObjectMixin, FileSharePermission, ProcessFormView):
    template_name =  get_template_name("files/share_people.html", APP_NAME)
    model = File
    form_class = ShareWithPeopleForm
    context_object_name = "file"

    def get_shared_people(self, file: File):
        user = self.get_user()
        return file.get_file_users(user=user)
    
    def get_form_kwargs(self):
        object = self.get_object()
        kwargs = super().get_form_kwargs()
        non_shared_people = object.get_non_shared_people()
        kwargs.update({"people": non_shared_people})
        return kwargs

    def get_context_data(self, **kwargs):
        context = kwargs
        object = self.get_object()
        share_people_form = self.get_form()
        shared_people = self.get_shared_people(object)

        context.update({
            "file": object,
            "share_people_form": share_people_form,
            "shared_people": shared_people,
        })
        return context

    def form_valid(self, form):
        user = self.get_user()
        object = self.get_object()
        people = form.cleaned_data["people"]

        permissions = {
            "can_read" : form.cleaned_data["can_read"],
            "can_write": form.cleaned_data["can_write"],
            "can_delete": form.cleaned_data["can_delete"],
        }
        kwargs = {
            "permissions" : permissions,
            "shared_by": user
        }
        
        object.add_people(people, **kwargs)

        hookset.file_shared_message(self.request, object)
        return redirect(object.get_absolute_url())

class FileRemoveGroup(UserMixin, DetailView):
    model = File
    
    def post(self, request, *args, **kwargs):
        object = self.get_object()
        groups = []
        groups.append(request.POST.get("group"))
        object.remove_groups(groups)
        return redirect(object.get_absolute_url())

class FileRemovePeople(UserMixin, DetailView):
    model = File

    def post(self, request, *args, **kwargs):
        object = self.get_object()
        people = []
        people.append(request.POST.get("people"))
        object.remove_people(people)
        return redirect(object.get_absolute_url())

class EmptyTrash(UserMixin, TemplateView):
    template_name =  get_template_name("trash/empty.html", APP_NAME)

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user = self.get_user()
        File.objects.empty_trash(user)
        return redirect(reverse(TRASH_URL))
    
class RestoreTrash(UserMixin, TemplateView):
    template_name =  get_template_name("trash/restore.html", APP_NAME)

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user = self.get_user()
        File.objects.restore_trash(user)
        return redirect(reverse(TRASH_URL))

class RemoveFile(UserMixin, DeleteView):
    template_name =  get_template_name("trash/remove_file.html", APP_NAME)
    model = File

    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return File.all_objects.get(pk=pk)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "file" : self.get_object()
        })
        return context
    
    def post(self, request, *args, **kwargs):
        object = self.get_object()
        object.permanent_delete()
        return redirect(reverse(TRASH_URL))

class RestoreFile(UserMixin, DetailView):
    template_name =  get_template_name("trash/restore_file.html", APP_NAME)
    model = File

    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return File.all_objects.get(pk=pk)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "file" : self.get_object()
        })
        return context
    
    def post(self, request, *args, **kwargs):
        object = self.get_object()
        object.restore()
        return redirect(reverse(TRASH_URL))