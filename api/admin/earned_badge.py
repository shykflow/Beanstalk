from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import EarnedBadge

class EarnedBadgeAdmin(admin.ModelAdmin):
    raw_id_fields = (
        'user',
        'badge',
        'experience',
        'experience_stack',
        'milestone',
    )
admin.site.register(EarnedBadge, EarnedBadgeAdmin, site=AppAdminSite)
