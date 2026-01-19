from typing import Any
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
    Playlist,
    Experience,
    Comment,
    Post,
    ExperienceAccept,
    ExperienceCompletion,
    ExperienceSave,
    SavePersonalBucketList
)
from lf_service.category import LifeFrameCategoryService


class ExperienceAttachmentInline(SoftDeleteTabularInlinePaginated):
    class Meta:
        ordering = ['-id']
    model = Attachment
    per_page = 5
    extra = 0
    fields = ('name', 'description', 'file', 'thumbnail', 'type', 'sequence',)
    classes = ['collapse']
    can_delete = True


class ExperiencePostInline(SoftDeleteTabularInlinePaginated):
    class Meta:
        ordering = ['-id']
    model = Post
    fields = ('created_by', 'text')
    raw_id_fields = ('created_by',)
    per_page = 50
    extra = 0
    formfield_overrides = {
        dj_models.CharField: {
            'widget': forms.Textarea(attrs={
                'rows':4,
                'cols': 100,
            }),
        },
    }
    classes = ['collapse']


class ExperienceCommentInline(TabularInlinePaginated):
    class Meta:
        ordering = ['-id']
    model = Comment
    fields = ('created_by', 'parent', '_mentions', 'text')
    raw_id_fields = ('created_by', 'parent',)
    readonly_fields = ('_mentions',)
    per_page = 50
    extra = 0
    formfield_overrides = {
        dj_models.CharField: {
            'widget': forms.Textarea(attrs={
                'rows':4,
                'cols': 100,
            })
        },
    }
    classes = ['collapse']
    def _mentions(self, obj: Comment) -> str:
        mentions = obj.mentions.all()
        return "\n".join([f'{u.id} - {u.username}' for u in mentions])


class ExperienceCostRatingsInline(TabularInlinePaginated):
    class Meta:
        ordering = ['-id']
    model = Experience.cost_ratings.through
    per_page = 20
    raw_id_fields = ('created_by', 'rating',)
    raw_id_fields = ('created_by',)
    verbose_name = "Cost Rating"
    verbose_name_plural = "Cost Ratings"
    classes = ['collapse']


class ExperienceStarRatingsInline(TabularInlinePaginated):
    class Meta:
        ordering = ['-id']
    model = Experience.star_ratings.through
    per_page = 20
    raw_id_fields = ('created_by', 'rating',)
    raw_id_fields = ('created_by',)
    verbose_name = "Star Rating"
    verbose_name_plural = "Star Ratings"
    classes = ['collapse']


class SharedWithInline(admin.TabularInline):
    model = Experience.shared_with.through
    per_page = 20
    extra = 0
    raw_id_fields = ('user',)
    verbose_name = "Shared With User"
    verbose_name_plural = "Shared With Users"
    classes = ['collapse']


class ExperienceAcceptInline(admin.TabularInline):
    model = ExperienceAccept
    per_page = 20
    extra = 0
    raw_id_fields = ('user',)
    verbose_name = "Accepted by User"
    verbose_name_plural = "Accepted by Users"
    classes = ['collapse']


class PlaylistInline(SoftDeleteTabularInlinePaginated):
    class Meta:
        ordering = ['-id']
    model = Playlist.experiences.through
    per_page = 20
    extra = 0
    fields = ('playlist',)
    raw_id_fields = ('playlist',)
    verbose_name = "Playlist"
    verbose_name_plural = "Playlists"
    classes = ['collapse']


class ExperienceCompleteInline(admin.TabularInline):
    model = ExperienceCompletion
    per_page = 20
    extra = 0
    raw_id_fields = ('user',)
    verbose_name = "Completed by User"
    verbose_name_plural = "Completed by Users"
    classes = ['collapse']


class ExperienceSaveInline(admin.TabularInline):
    model = ExperienceSave
    per_page = 20
    extra = 0
    raw_id_fields = ('user',)
    verbose_name = "Saved for later by User"
    verbose_name_plural = "Saved for later by Users"
    classes = ['collapse']


class ExperienceSaveToBucketListInline(admin.TabularInline):
    model = SavePersonalBucketList
    per_page = 20
    extra = 0
    raw_id_fields = ('user',)
    verbose_name = "Saved to bucket list by User"
    verbose_name_plural = "Saved to bucket list by Users"
    classes = ['collapse']


class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        ordering = ['-id']
        # Django Admin requires either "fields" or "exclude"
        # See the "fieldsets" of the main Admin class to see
        # what fields are included.
        exclude = tuple()

    def clean_categories(self):
        input_category_ids = self.cleaned_data['categories']
        if 'categories' not in self.changed_data:
            return input_category_ids
        if len(input_category_ids) == 0:
            return input_category_ids
        # Check for duplicates
        checked_ids = []
        duplicate_ids = []
        for id in input_category_ids:
            if id not in checked_ids:
                checked_ids.append(id)
            else:
                duplicate_ids.append(id)
        if len(duplicate_ids) > 0:
            str_ids = [str(id) for id in duplicate_ids]
            raise forms.ValidationError(f'Duplicate IDs: {",".join(str_ids)}')

        # Check if all newly added IDs exist in LifeFrame
        new_ids: list[int]
        if self.instance.categories is not None:
            new_ids = [
                id
                for id in input_category_ids
                if id not in self.instance.categories
            ]
        else:
            new_ids = input_category_ids
        lf_category_service = LifeFrameCategoryService()
        _, unknown_category_ids = lf_category_service.list(new_ids)
        if len(unknown_category_ids) > 0:
            msg = f'These IDs {unknown_category_ids} ' + \
                'do not exist in Life Frame'
            raise forms.ValidationError(msg)
        return input_category_ids


class QCReviewedFilter(SimpleListFilter):
    title = 'QC Reviewed'
    parameter_name: str = 'qc_reviewed'
    def lookups(self, request, model_admin):
        return (
            ('true', 'Is reviewed'),
            ('false', 'Is not reviewed'),
        )
    def queryset(self, request, queryset):
        value = self.value()
        if value == 'true':
            return queryset.filter(qc_reviewed=True)
        elif value == 'false':
            return queryset.filter(qc_reviewed=False)
        return queryset


class ExperienceAdmin(SoftDeleteModelAdmin):
    class Meta:
        ordering = ['-id']

    form = ExperienceForm
    list_display = (
        'name',
        'created_by',
        'difficulty',
        'created_at',
        '_average_star_rating',
        '_average_cost_rating',
        'qc_reviewed',
        'publicly_viewable',
    )
    search_fields = (
        'name',
        'created_by__username',
        'created_by__email',
    )
    list_filter = SoftDeleteModelAdmin.list_filter + (
        QCReviewedFilter,
        ManagedUserFilter,
    )
    fieldsets = (
        (None, {
            'fields': (
            'qc_reviewed',
            'created_by',
            'created_at',
            'name',
            'categories',
            'custom_categories',
            'description',
            'admin_mentions_html',
            'difficulty',
            'visibility',
            'location',
            'latitude',
            'longitude',
            'phone',
            'original_id',
            'original_data',
            ),
        }),

        ('Links', {
            'fields': (
                'website',
                'reservation_link',
                'menu_link',
                'purchase_link',
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
            )
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
        'location',
        'latitude',
        'longitude',
        'total_likes',
        'total_comments',
        'total_accepts',
        'total_completes',
        'total_reviews',
        '_average_star_rating',
        '_average_cost_rating',
    )
    raw_id_fields = ('created_by', 'custom_categories')
    inlines = (
        ExperienceAttachmentInline,
        PlaylistInline,
        ExperiencePostInline,
        ExperienceCommentInline,
        ExperienceCostRatingsInline,
        ExperienceStarRatingsInline,
        SharedWithInline,
        ExperienceAcceptInline,
        ExperienceCompleteInline,
        ExperienceSaveInline,
        ExperienceSaveToBucketListInline,
        ReportInline,
    )

    def _average_star_rating(self, experience: Experience):
        if experience.average_star_rating is None:
            return None
        return round(experience.average_star_rating, 2)

    def _average_cost_rating(self, experience: Experience):
        if experience.average_cost_rating is None:
            return None
        return round(experience.average_cost_rating, 2)

    def get_form(self, request, obj=None, **kwargs):
        kwargs['widgets'] = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'not_publicly_viewable_reason': forms.Textarea(attrs={'rows': 5}),
        }
        return super().get_form(request, obj, **kwargs)

admin.site.register(Experience, ExperienceAdmin, site=AppAdminSite)
