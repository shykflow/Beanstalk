from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from sponsorship.models import (
    ExperienceSponsorship,
)

class ExperienceSponsorshipAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'experience',)
admin.site.register(ExperienceSponsorship, ExperienceSponsorshipAdmin, site=AppAdminSite)
