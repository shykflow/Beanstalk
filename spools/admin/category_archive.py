from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from spools.models import CategoryArchiveSpool

class CategoryArchiveSpoolAdmin(admin.ModelAdmin):
    fields = (
        'category_id',
        'change_to',
    )

admin.site.register(CategoryArchiveSpool, CategoryArchiveSpoolAdmin, site=AppAdminSite)
