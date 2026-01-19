from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import Activity

class ActivityAdmin(admin.ModelAdmin):
    raw_id_fields = (
        'user',
        'related_user',
        'post',
        'comment',
        'related_comment',
        'experience',
        'playlist',
        'experience_stack',
    )
    # Uncomment as needed
    # list_filter = (
    #     'comment',
    #     'related_comment',
    #     'type',
    # )

admin.site.register(Activity, ActivityAdmin, site=AppAdminSite)
