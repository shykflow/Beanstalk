from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db import models as dj_models
from django_admin_inline_paginator.admin import TabularInlinePaginated

from api.admin.abstract.soft_delete_model_admin import (
    SoftDeleteModelAdmin,
    SoftDeleteTabularInlinePaginated,
)
from api.admin.admin_site import AppAdminSite
from api.admin.report import ReportInline
from api.admin.managed_user import ManagedUserFilter
from api.models import (
    Attachment,
    Comment,
    Post,
)

class PostAttachmentInline(SoftDeleteTabularInlinePaginated):
    model = Attachment
    per_page = 5
    extra = 0
    fields = ('name', 'description', 'file', 'thumbnail', 'type', 'sequence',)
    classes = ['collapse']
    can_delete = True


class PostCommentInline(TabularInlinePaginated):
    model = Comment
    # def get_a(self, obj):

    raw_id_fields = ('created_by', 'parent',)
    fields = (
        'created_by',
        'parent',
        '_mentions',
        'text',
        'publicly_viewable',
        'not_publicly_viewable_reason',
    )
    readonly_fields = ('_mentions',)
    classes = ['collapse']
    per_page = 50
    extra = 0
    formfield_overrides = {
        dj_models.CharField: {'widget': forms.Textarea(attrs={'rows':4, 'cols': 40})},
    }
    def _mentions(self, obj: Comment) -> str:
        mentions = obj.mentions.all()
        return "\n".join([f'{u.id} - {u.username}' for u in mentions])


class TypeFilter(SimpleListFilter):
    title = 'Type'
    parameter_name: str = 'type'
    def lookups(self, request, model_admin):
        return (
            ('experience', 'Experience Posts'),
            ('playlist', 'Playlist Posts'),
            ('no_references', 'No Content Posts')
        )
    def queryset(self, request, queryset):
        value = self.value()
        if value == 'experience':
            return queryset.filter(experience__isnull=False)
        if value == 'playlist':
            return queryset.filter(playlist__isnull=False)
        if value == 'no_references':
            return queryset.filter(experience__isnull=True, playlist__isnull=True)
        return queryset


class CompletionFilter(SimpleListFilter):
    title = 'Completion'
    parameter_name: str = 'completion'
    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )
    def queryset(self, request, queryset):
        value = self.value()
        if value == 'yes':
            return queryset.exclude(experience_completion=None, playlist_completion=None)
        if value == 'no':
            return queryset.filter(experience_completion=None, playlist_completion=None)
        return queryset


class PostAdmin(SoftDeleteModelAdmin):
    search_fields = (
        'created_by__email',
        'created_by__username',
        'experience__name',
        'playlist__name',
        'name',
    )
    raw_id_fields = (
        'parent',
        'created_by',
        'experience',
        'playlist',
        'experience_completion',
        'playlist_completion',
    )
    list_display = (
        'created_by',
        'name',
        'truncated_text',
        'parent',
        'experience_completion',
        'playlist_completion',
        'experience',
        'playlist',
    )
    fieldsets = (
        (None, {
            'fields': (
                'name',
                'text',
                'admin_mentions_html',
                'created_by',
                'created_at',
                'experience_completion',
                'playlist_completion',
            ),
        }),
        ('Posted On', {
            'fields': (
                'parent',
                'experience',
                'playlist',
            ),
        }),
        ('Media', {
            'fields': (
                'video',
                'highlight_image',
            ),
        }),
        ('Viewability', {
            'fields': (
                'publicly_viewable',
                'not_publicly_viewable_reason',
            ),
        }),
        ('Aggregates', {
            'fields': (
                'total_likes',
                'total_comments',
            ),
        }),
    )
    readonly_fields = (
        'created_at',
        'total_likes',
        'total_comments',
        'admin_mentions_html',
    )
    inlines = (
        PostAttachmentInline,
        PostCommentInline,
        ReportInline,
    )
    list_filter = SoftDeleteModelAdmin.list_filter + (
        TypeFilter,
        ManagedUserFilter,
        CompletionFilter,
    )

    def get_form(self, request, obj=None, **kwargs):
        kwargs['widgets'] = {
            'text': forms.Textarea(attrs={'rows': 5}),
            'not_publicly_viewable_reason': forms.Textarea(attrs={'rows': 5}),
        }
        return super().get_form(request, obj, **kwargs)


    @admin.display(
        description='Text')
    def truncated_text(self, post: Post):
        if len(post.text) > 50:
            return post.text[0:50] + '...'
        return post.text

admin.site.register(Post, PostAdmin, site=AppAdminSite)
