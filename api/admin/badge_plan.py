from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import BadgePlan

class BadgePlanAdmin(admin.ModelAdmin):
    pass
admin.site.register(BadgePlan, BadgePlanAdmin, site=AppAdminSite)
