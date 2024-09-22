from django.urls import path

from . import views

urlpatterns = [

    path("home", views.Index.as_view(), name="home"),
    path("mydrive", views.MyDrive.as_view(), name="mydrive"),

    path("recent", views.RecentView.as_view(), name="recent"),

    path("trash", views.TrashView.as_view(), name="trash"),
    path("trash/empty", views.EmptyTrash.as_view(), name="empty_trash"),
    path("trash/restore", views.RestoreTrash.as_view(), name="restore_trash"),
    path("trash/<uuid:pk>/remove_file", views.RemoveFile.as_view(), name="remove_file"),
    path("trash/<uuid:pk>/restore_file", views.RestoreFile.as_view(), name="restore_file"),

    path("shared", views.SharedView.as_view(), name="shared"),
    path("shared/<uuid:pk>", views.SharedFile.as_view(), name="shared_file"),

    path("group/<uuid:pk>", views.GroupView.as_view(), name="group"),
    path("group/<uuid:pk>/members", views.GroupMembersView.as_view(), name="group_members"),
    path("group/<uuid:pk>/remove/member", views.GroupRemoveMember.as_view(), name="remove_member"),
    path("group/<uuid:pk>/admin", views.GroupAdmin.as_view(), name="group_admin"),

    path("folder/create/", views.FolderCreate.as_view(), name="folder_create"),
    path("file/upload", views.FileUpload.as_view(), name="file_upload"),
    path("file/<uuid:pk>", views.FileView.as_view(), name="file_view"),
    path("file/<uuid:pk>/info", views.FileInfo.as_view(), name="file_info"),
    path("file/<uuid:pk>/update", views.FileUpdate.as_view(), name="file_update"),
    path("file/<uuid:pk>/download", views.FileDownload.as_view(), name="file_download"),
    path("file/<uuid:pk>/delete", views.FileDelete.as_view(), name="file_delete"),
    path("file/<uuid:pk>/rename", views.FileRename.as_view(), name="file_rename"),
    path("file/<uuid:pk>/organize", views.FileOrganize.as_view(), name="file_organize"),
    path("file/<uuid:pk>/share/group", views.FileShareWithGroup.as_view(), name="file_share_group"),
    path("file/<uuid:pk>/share/people", views.FileShareWithPeople.as_view(), name="file_share_people"),
    path("file/<uuid:pk>/unshare/group", views.FileRemoveGroup.as_view(), name="file_remove_group"),
    path("file/<uuid:pk>/unshare/people", views.FileRemovePeople.as_view(), name="file_remove_people"),

]
