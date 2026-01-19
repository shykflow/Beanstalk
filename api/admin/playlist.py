from django import forms
from django.contrib import admin
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
    Playlist,
    Comment,
    Post,
    PlaylistAccept,
    PlaylistCompletion,
    PlaylistSave,
)

class PlaylistAttachmentInline(SoftDeleteTabularInlinePaginated):
    model = Attachment
    per_page = 5
    extra = 0
    fields = ('name', 'description', 'file', 'thumbnail', 'type', 'sequence',)
    classes = ('collapse',)
    can_delete = True


class PlaylistPostInline(SoftDeleteTabularInlinePaginated):
    model = Post
    per_page = 50
    extra = 0
    raw_id_fields = ('created_by',)
    fields = ('created_by', 'text',)
    formfield_overrides = {
        dj_models.CharField: {'widget': forms.Textarea(attrs={'rows':4, 'cols': 100})},
    }
    classes = ('collapse',)


class PlaylistCommentInline(TabularInlinePaginated):
    model = Comment
    raw_id_fields = ('created_by', 'parent',)
    fields = ('created_by', 'parent', '_mentions', 'text',)
    readonly_fields = ('_mentions',)
    per_page = 50
    extra = 0
    formfield_overrides = {
        dj_models.CharField: {'widget': forms.Textarea(attrs={'rows':4, 'cols': 100})},
    }
    classes = ('collapse',)
    def _mentions(self, obj: Comment) -> str:
        mentions = obj.mentions.all()
        return "\n".join([f'{u.id} - {u.username}' for u in mentions])


class PlaylistCostRatingsInline(TabularInlinePaginated):
    model = Playlist.cost_ratings.through
    per_page = 20
    raw_id_fields = ('created_by', 'rating',)
    raw_id_fields = ('created_by',)
    verbose_name = "Cost Rating"
    verbose_name_plural = "Cost Ratings"
    classes = ['collapse']


class PlaylistStarRatingsInline(TabularInlinePaginated):
    model = Playlist.star_ratings.through
    per_page = 20
    raw_id_fields = ('created_by', 'rating',)
    raw_id_fields = ('created_by',)
    verbose_name = "Star Rating"
    verbose_name_plural = "Star Ratings"
    classes = ['collapse']


class ExperienceInline(SoftDeleteTabularInlinePaginated):
    model = Playlist.experiences.through
    per_page = 20
    extra = 0
    fields = ('experience',)
    raw_id_fields = ('experience',)
    verbose_name_plural = "Experiences"
    classes = ('collapse',)


class PlaylistAcceptInline(admin.TabularInline):
    model = PlaylistAccept
    per_page = 20
    extra = 0
    raw_id_fields = ('user',)
    verbose_name = "Accepted by User"
    verbose_name_plural = "Accepted by Users"
    classes = ('collapse',)


class PlaylistCompleteInline(admin.TabularInline):
    model = PlaylistCompletion
    per_page = 20
    extra = 0
    raw_id_fields = ('user',)
    verbose_name = "Completed by User"
    verbose_name_plural = "Completed by Users"
    classes = ('collapse',)


class PlaylistSaveInline(admin.TabularInline):
    model = PlaylistSave
    per_page = 20
    extra = 0
    raw_id_fields = ('user',)
    verbose_name = "Saved for later by User"
    verbose_name_plural = "Saved for later by Users"
    classes = ('collapse',)


class PlaylistAdmin(SoftDeleteModelAdmin):
    list_display = (
        'name',
        'created_by',
        'editability',
        # 'aggregated_categories',
        'start',
        'end',
    )
    raw_id_fields = (
        'created_by',
    )
    fieldsets = (
        (None, {
            'fields': (
                'name',
                'description',
                'admin_mentions_html',
                'created_by',
                'created_at',
                'editability',
                'visibility',
            ),
        }),
        ('Media', {
            'fields': (
                'video',
                'highlight_image',
                'highlight_image_thumbnail',
            ),
        }),
        ('Time', {
            'fields': (
                'start_time',
                'start_time_date_only',
                'end_time',
                'end_time_date_only',
                'use_local_time',
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
                'aggregated_categories',
                'total_likes',
                'total_comments',
                'total_accepts',
                'total_completes',
                'total_reviews',
                '_average_star_rating',
                '_average_cost_rating',
            ),
        }),
    )
    readonly_fields = (
        'created_at',
        'admin_mentions_html',
        'aggregated_categories',
        'total_likes',
        'total_comments',
        'total_accepts',
        'total_completes',
        'total_reviews',
        '_average_star_rating',
        '_average_cost_rating',
    )
    search_fields = (
        'name',
        'created_by__username',
    )
    inlines = (
        ExperienceInline,
        PlaylistAttachmentInline,
        PlaylistPostInline,
        PlaylistCommentInline,
        PlaylistCostRatingsInline,
        PlaylistStarRatingsInline,
        PlaylistAcceptInline,
        PlaylistCompleteInline,
        PlaylistSaveInline,
        ReportInline,
    )
    list_filter = SoftDeleteModelAdmin.list_filter + (
        ManagedUserFilter,
    )

    def _average_star_rating(self, playlist: Playlist):
        if playlist.average_star_rating is None:
            return None
        return round(playlist.average_star_rating, 2)

    def _average_cost_rating(self, playlist: Playlist):
        if playlist.average_cost_rating is None:
            return None
        return round(playlist.average_cost_rating, 2)


    # override
    def save_model(self, request, obj: Playlist, *args) -> None:
        obj.update_aggregated_categories()
        return super().save_model(request, obj, *args)

    def get_form(self, request, obj=None, **kwargs):
        kwargs['widgets'] = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'not_publicly_viewable_reason': forms.Textarea(attrs={'rows': 5}),
        }
        return super().get_form(request, obj, **kwargs)

admin.site.register(Playlist, PlaylistAdmin, site=AppAdminSite)
