from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import Showcase

class ShowcaseAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
admin.site.register(Showcase, ShowcaseAdmin, site=AppAdminSite)
