from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from sponsorship.models import (
    PlaylistSponsorship,
)
class PlaylistSponsorshipAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'playlist',)
admin.site.register(PlaylistSponsorship, PlaylistSponsorshipAdmin, site=AppAdminSite)

