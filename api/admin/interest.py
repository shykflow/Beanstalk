from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import Interest

class InterestAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
admin.site.register(Interest, InterestAdmin, site=AppAdminSite)
