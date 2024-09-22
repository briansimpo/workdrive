
from django import forms
from .models import Document, File, Folder


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class UserMultipleChoiceField(forms.ModelMultipleChoiceField):

    def label_from_instance(self, obj):
        return obj

class GroupMultipleChoiceField(forms.ModelMultipleChoiceField):

    def label_from_instance(self, obj):
        return obj

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class FolderCreateForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ["name", "group", "parent"]
        widgets = {
            "group": forms.HiddenInput,
            "parent": forms.HiddenInput
        }

class FileUpdateForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ["description", "published", "can_read", "can_write", "can_delete"]

class FileUploadForm(forms.ModelForm):
    file = MultipleFileField()
    class Meta:
        model = Document
        fields = ["file", "group", "parent"]
        widgets = {
            "group": forms.HiddenInput,
            "parent": forms.HiddenInput,
        }

class FileRenameForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ["name"]

class FileOrganizeForm(forms.ModelForm):
    parent = forms.ModelChoiceField(queryset=None, required=False, label="Move To")

    class Meta:
        model = Folder
        fields = ["parent"]

    def __init__(self, *args, **kwargs):
        folders = kwargs.pop("folders")
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = folders

class ShareWithGroupForm(forms.Form):
    groups = GroupMultipleChoiceField(
        queryset=None,
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-control",
                "data-placeholder": "Choose groups... "
            }
        )
    )
    can_read = forms.BooleanField(label="Can Read", initial=True, required=False)
    can_write = forms.BooleanField(label="Can Write", initial=False, required=False)
    can_delete = forms.BooleanField(label="Can Delete", initial=False, required=False)

    class Meta:
        fields = ["groups", "can_write", "can_read", "can_delete"]

    def __init__(self, *args, **kwargs):
        groups = kwargs.pop("groups")
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = groups

class ShareWithPeopleForm(forms.Form):
    people = UserMultipleChoiceField(
        queryset=None,
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-control",
                "data-placeholder": "Choose people... "
            }
        )
    )
    can_read = forms.BooleanField(label="Can Read", initial=True, required=False)
    can_write = forms.BooleanField(label="Can Write", initial=False, required=False)
    can_delete = forms.BooleanField(label="Can Delete", initial=False, required=False)

    class Meta:
        fields = ["people", "can_write", "can_read", "can_delete"]

    def __init__(self, *args, **kwargs):
        people = kwargs.pop("people")
        super().__init__(*args, **kwargs)
        self.fields["people"].queryset = people

class GroupMemberForm(forms.Form):
    members = GroupMultipleChoiceField(
        queryset=None,
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-control",
                "data-placeholder": "Choose members... "
            }
        )
    )

    class Meta:
        fields = ["members"]

    def __init__(self, *args, **kwargs):
        members = kwargs.pop("members")
        super().__init__(*args, **kwargs)
        self.fields["members"].queryset = members