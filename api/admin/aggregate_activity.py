from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import AggregateActivity

class AggregateActivityAdmin(admin.ModelAdmin):
    readonly_fields = (
        "user",
        "type",
        "count",
        "post",
        "comment",
        "related_comment",
        "experience",
        "playlist",
        "experience_stack",
        "created_at",
        "related_time",
        "related_user",
    )
    # Uncomment as needed
    # list_filter = ('related_user', 'type', 'user',)


admin.site.register(AggregateActivity, AggregateActivityAdmin, site=AppAdminSite)
