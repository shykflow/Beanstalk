from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import BadgeTemplate

class BadgeTemplateAdmin(admin.ModelAdmin):
    pass
admin.site.register(BadgeTemplate, BadgeTemplateAdmin, site=AppAdminSite)
