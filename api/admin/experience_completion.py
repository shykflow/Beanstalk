from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import ExperienceCompletion

class ExperienceCompletionAdmin(admin.ModelAdmin):
    raw_id_fields = (
        'completed_by',
        'experience',
    )
admin.site.register(ExperienceCompletion, ExperienceCompletionAdmin, site=AppAdminSite)
