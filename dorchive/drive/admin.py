from django.contrib import admin

from .models import (
    File, 
    GroupFile, 
    UserFile, 
    Group,
    UserGroup,
)


class GroupAdmin(admin.ModelAdmin):
    list_display = ["name", "is_public"]
    list_display_links = ["name",]
    search_fields = ["name",]

class FileAdmin(admin.ModelAdmin):
    list_display = ["name", "group", "parent",  "file",  "original_filename", "author", "file_type", "modified_by"]
    list_display_links = ["name", "group", "parent"]
    search_fields = ["name",]

class GroupFileAdmin(admin.ModelAdmin):
    list_display = ["group", "file", "can_read",  "can_write", "can_delete"]
    list_display_links = ["group", "file"]

class UserFileAdmin(admin.ModelAdmin):
    list_display = ["user", "file", "can_read",  "can_write", "can_delete"]
    list_display_links = ["user", "file"]

class UserGroupAdmin(admin.ModelAdmin):
    list_display = ["user", "group", "is_admin"]
    list_display_links = ["user", "group"]

admin.site.register(Group, GroupAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(GroupFile, GroupFileAdmin)
admin.site.register(UserFile, UserFileAdmin)
admin.site.register(UserGroup, UserGroupAdmin)


