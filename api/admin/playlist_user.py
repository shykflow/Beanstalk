from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import PlaylistUser

class PlaylistUserAdmin(admin.ModelAdmin):
    raw_id_fields = ('playlist', 'user',)
admin.site.register(PlaylistUser, PlaylistUserAdmin, site=AppAdminSite)
