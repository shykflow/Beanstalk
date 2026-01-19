from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import Badge

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    pass
admin.site.register(Badge, BadgeAdmin, site=AppAdminSite)
