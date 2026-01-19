from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import PowerProfileAdmin

class PowerProfileAdminAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
admin.site.register(PowerProfileAdmin, PowerProfileAdminAdmin, site=AppAdminSite)
