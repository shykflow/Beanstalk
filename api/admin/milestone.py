from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import Milestone

class MilestoneAdmin(admin.ModelAdmin):
    pass
admin.site.register(Milestone, MilestoneAdmin, site=AppAdminSite)
