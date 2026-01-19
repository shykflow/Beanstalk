from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import Device

class DeviceAdmin(admin.ModelAdmin):
    model = Device
    search_fields = (
        'user__username',
        'user__email',
    )
    list_display = (
        'user',
        # 'token',
        'os',
        'minutes_offset',
        'last_check_in',
    )
    fields = (
        'user',
        'details',
        'token',
        'last_check_in',
        'minutes_offset',
        'os',
    )
    readonly_fields = (
        'user',
        'details',
        'token',
        'last_check_in',
        'os',
        'minutes_offset',
    )
    raw_id_fields = (
        'user',
    )
admin.site.register(Device, DeviceAdmin, site=AppAdminSite)
