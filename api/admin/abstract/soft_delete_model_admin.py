from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.forms import ModelForm
from django.utils.safestring import mark_safe
from django.urls import reverse
from django_admin_inline_paginator.admin import TabularInlinePaginated

from api.models.abstract.soft_delete_model import SoftDeleteModel
from api.models import (
    Attachment,
    Experience,
    Playlist,
    Post,
)


class SoftDeleteFilter(SimpleListFilter):
    title = 'Soft Deleted'
    parameter_name = 'soft_deleted'
    def lookups(self, request, model_admin):
        return (
            ('true', 'Soft Deleted'),
            ('false', 'Not Soft Deleted'),
        )
    def queryset(self, request, queryset):
        value = self.value()
        if value == 'true':
            return queryset.filter(is_deleted=True)
        elif value == 'false':
            return queryset.filter(is_deleted=False)
        return queryset


class SoftDeleteModelAdmin(admin.ModelAdmin):
    """
    Register models that inherit from SoftDeleteModel with this class to
    automatically show and handle soft deleting.

    ```
    class Foo(SoftDeleteModel):
        pass

    @admin.register(Foo)
    class FooAdmin(SoftDeleteModelAdmin):
        pass
    ```

    Set `show_deleted_in_list_display = False` to stop the default
    behavior of showing if an item is soft deleted in the list displays.
    """

    list_filter = (
        SoftDeleteFilter,
    )

    show_deleted_in_list_display = True

    delete_confirmation_template = 'admin_soft_delete_confirmation.html'
    delete_selected_confirmation_template = 'admin_soft_delete_selected_confirmation.html'
    _deleted_html_field_name = 'deleted_html'
    _unlabeled_fieldset = (None, {
        'fields': (
            _deleted_html_field_name,
        ),
    })

    def get_queryset(self, request):
        return self.model.all_objects.all()

    def delete_queryset(self, request, queryset):
        obj: SoftDeleteModel
        for obj in queryset:
            if obj.is_deleted:
                continue
            obj.delete()

    def get_readonly_fields(self, request, obj: SoftDeleteModel):
        super_fields = super().get_readonly_fields(request, obj)
        if obj is None:
            return super_fields
        fields = list(super_fields) if super_fields is not None else []
        fields.append(self._deleted_html_field_name)
        return fields

    def get_fieldsets(self, request, obj: SoftDeleteModel):
        super_fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            return super_fieldsets
        if not obj.is_deleted:
            return super_fieldsets
        fieldsets = list(super_fieldsets) if super_fieldsets is not None else []
        if fieldsets is None or len(fieldsets) == 0:
            return [
                self._unlabeled_fieldset,
            ]
        has_unlabel_section_first = fieldsets[0][0] == None
        if has_unlabel_section_first:
            fields = list(fieldsets[0][1]['fields'])
            fields.insert(0, self._deleted_html_field_name)
            fieldsets[0][1]['fields'] = fields
        else:
            fieldsets.insert(0, self._unlabeled_fieldset,)
        return fieldsets

    def get_fields(self, request, obj: SoftDeleteModel):
        super_fields = super().get_fields(request, obj)
        if obj is None:
            return super_fields
        fields = list(super_fields) if super_fields is not None else []
        if obj.is_deleted and self._deleted_html_field_name not in fields:
            fields.insert(0, self._deleted_html_field_name)
        return fields

    def get_list_display(self, request):
        if not self.show_deleted_in_list_display:
            return super().get_list_display(request)
        list_display = list(super().get_list_display(request))
        list_display.append(self._deleted_html_field_name)
        return list_display


    @admin.display(
        ordering='is_deleted',
        description='DELETED')
    def deleted_html(self, obj: SoftDeleteModel):
        if obj.is_deleted:
            return mark_safe('''
                <p style="color: red; font-weight: bold;">
                    DELETED
                </p>
            ''')
        return '-'


class SoftDeleteInlineForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'experience' in self.fields:
            self.fields['experience'].queryset = Experience.all_objects.all()
        if 'playlist' in self.fields:
            self.fields['playlist'].queryset = Playlist.all_objects.all()
        if 'post' in self.fields:
            self.fields['post'].queryset = Post.all_objects.all()

    def is_valid(self) -> bool:
        """
        For cases where `self.instance` is the `SoftDeleteModel` itself
        (Attachments), it was proving difficult to ignore the 'Select a valid
        choice. That choice is not one of the available choices.' issue.

        The problem is that in these cases, `self.fields` contains the fields of
        of the model itself (meaning if `self.instance` is an Attachment, the
        fields doesn't contain an 'attachment' field.) so there isn't a clear
        place to override the queryset and force it `all_objects.all()`.

        This method overrides `is_valid` and forces the return to be true in the
        exact case that it was not valid, the 'id' was the error, and the
        instance is soft deleted.
        """
        valid = super().is_valid()
        if not valid and 'id' in self.errors:
            return getattr(self.instance, 'is_deleted', False) == True
        return valid


class SoftDeleteTabularInlinePaginated(TabularInlinePaginated):
    """
    Django's `ModelChoiceField` will use the `objects` manager by default,
    which for soft delete models means it filters out soft deletes.
    This causes "Select a valid choice. That choice is not one of the available
    choices." to be shown when saving an inline.

    This class handles both cases where the inline's model is a soft delete
    model (like `PlaylistAttachmentInline`) or the m2m is a soft delete (like
    `UserCompletedExperienceInline`).
    """
    form = SoftDeleteInlineForm

    def __init__(self, *args, **kwargs):
        if not getattr(self, 'fields', False):
            raise Exception("Must specify 'fields'")
        self.fields += ('soft_deleted',)
        if getattr(self, 'readonly_fields'):
            self.readonly_fields += ('soft_deleted',)
        else:
            self.readonly_fields = ('soft_deleted',)
        self.model_is_soft_delete = issubclass(self.model, SoftDeleteModel)
        super().__init__(*args, **kwargs)

    def get_queryset(self, request):
        if self.model_is_soft_delete:
            qs = self.model.all_objects.all()
            ordering = self.get_ordering(request)
            if ordering:
                qs = qs.order_by(*ordering)
            return qs
        return super().get_queryset(request)

    def soft_deleted(self, record):
        instance: Attachment | Experience | Playlist | Post
        if self.model_is_soft_delete:
            instance = record
        else:
            if 'experience' in self.fields:
                instance = record.experience
            elif 'playlist' in self.fields:
                instance = record.playlist
            elif 'post' in self.fields:
                instance = record.post
            else:
                raise Exception('Unsupported soft delete type')
        cannot_be_linked_to = type(instance) is Attachment
        if instance.is_deleted:
            inner_text = f'''
                <span style="color: #FF0000; font-weight: bold;">DELETED</span>
                {instance}'''
            if cannot_be_linked_to:
                return mark_safe(inner_text)
            info = (instance._meta.app_label, instance._meta.model_name)
            admin_url = reverse('admin:%s_%s_change' % info, args=(instance.pk,))
            return mark_safe(f'''
                <a href="{admin_url}">
                    {inner_text}
                </a>''')
        return '-'
