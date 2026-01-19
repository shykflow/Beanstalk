from django.contrib import admin
from rest_framework.authtoken.models import Token

from api.admin.admin_site import AppAdminSite

class TokenAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'key',
    )
    raw_id_fields = (
        'user',
    )
admin.site.register(Token, TokenAdmin, site=AppAdminSite)
