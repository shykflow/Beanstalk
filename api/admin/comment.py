from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.admin.report import ReportInline
from api.models import Comment


class CommentAdmin(admin.ModelAdmin):
    raw_id_fields = (
        'created_by',
        'parent',
        'post',
        'experience',
        'playlist',
    )
    search_fields = (
        'id',
        'parent__id',
        'created_by__username',
        'created_by__email',
        'text',
    )
    list_display = (
        '__str__',
        'id',
        'parent_id',
        'created_by',
        'created_at',
    )
    fields = (
        'created_by',
        'text',
        'parent',
        'post',
        'playlist',
        'experience',
        '_mentions',
        'total_likes',
        'total_comments',
    )
    readonly_fields = (
        'total_likes',
        'total_comments',
        '_mentions',
    )
    inlines = (
        ReportInline,
    )

    def _mentions(self, obj: Comment) -> str:
        mentions = obj.mentions.all()
        return "\n".join([f'{u.id} - {u.username}' for u in mentions])

    def has_module_permission(self, request) -> bool:
        return False

admin.site.register(Comment, CommentAdmin, site=AppAdminSite)
