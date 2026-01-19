from django import forms
from django.contrib import admin
from django.contrib.admin import (
    ModelAdmin,
    SimpleListFilter,
)
from django.http.request import HttpRequest
from django_admin_inline_paginator.admin import TabularInlinePaginated

from api.admin.admin_site import AppAdminSite
from api.models import Report

class ReportInline(TabularInlinePaginated):
    """
    Subclass this and define the fields to hide some
    """
    model = Report
    per_page = 50
    extra = 0
    fields = (
        'acknowledged',
        'created_by',
        'offender',
        'type',
        'details',
        'cron_emailed',
    )
    readonly_fields = (
        'created_by',
        'offender',
        'type',
        'details',
        'cron_emailed',
        'experience',
        'playlist',
        'post',
        'comment',
    )
    raw_id_fields = (
        'created_by',
        'offender',
        'playlist',
        'experience',
        'post',
        'comment',
    )
    classes = ['collapse']
    can_delete = False




class AcknowledgedFilter(SimpleListFilter):
    title = 'Acknowledged'
    parameter_name: str = 'acknowledged'
    def lookups(self, request, model_admin):
        return (
            ('true', 'Is acknowledged'),
            ('false', 'Is not acknowledged'),
        )
    def queryset(self, request, queryset):
        value = self.value()
        if value == 'true':
            return queryset.filter(acknowledged=True)
        elif value == 'false':
            return queryset.filter(acknowledged=False)
        return queryset


class ReportAdmin(ModelAdmin):
    search_fields = (
        'created_by',
        'offender',
        'type',
    )
    list_display = (
        'created_by',
        'offender',
        'content_type',
        'type',
        '_details',
        'created_at',
        'cron_emailed',
        'acknowledged',
    )

    search_fields = (
        'created_by__username',
        'created_by__email',
        'offender__username',
        'offender__email',
    )

    raw_id_fields = (
        'created_by',
        'offender',
        'playlist',
        'experience',
        'post',
        'comment',
    )
    fieldsets = (
        (None, {
            'fields': (
                'acknowledged',
                'created_by',
                'offender',
                'type',
                'details',
                'cron_emailed',
                'playlist',
                'experience',
                'post',
                'comment',
            ),
        }),
    )

    list_filter = (
        AcknowledgedFilter,
    )

    def content_type(self, report: Report):
        if report.playlist is not None:
            return 'Playlist'
        if report.experience is not None:
            return 'Experience'
        if report.post is not None:
            if report.post.playlist is not None:
                return 'Playlist Post'
            if report.post.experience is not None:
                return 'Experience Post'
            return 'Misconfigured Post'
        if report.comment is not None:
            return 'Comment'
        return 'User'

    def _details(self, report: Report):
        details = report.details
        if details is None:
            return None
        if len(details) < 100:
            return details
        return details[:100] + '...'

    def get_form(self, request, obj=None, **kwargs):
        kwargs['widgets'] = {
            'details': forms.Textarea(attrs={'rows': 5}),
        }
        return super().get_form(request, obj, **kwargs)

admin.site.register(Report, ReportAdmin, site=AppAdminSite)
