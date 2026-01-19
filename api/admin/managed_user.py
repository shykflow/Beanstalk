from django.contrib import admin
from django.contrib.admin import (
    ModelAdmin,
    SimpleListFilter,
)
from api.admin.admin_site import AppAdminSite

from api.models import (
    ManagedUser,
)


class ManagedUserFilter(SimpleListFilter):
    title = 'Managed User'
    parameter_name: str = 'created_by_managed'
    def lookups(self, request, model_admin):
        managed_users = list(ManagedUser.objects.values_list('user__id', 'user__username'))
        return [(x[0], x[1]) for x in managed_users]
    def queryset(self, request, queryset):
        value: str = self.value()
        if value is None or not value.isdigit():
            return queryset
        value_int = int(value)
        qs = queryset.filter(created_by__id=value_int)
        if qs.exists():
            return qs
        return queryset


class ManagedUserAdmin(ModelAdmin):
    search_fields = (
        'user__email',
        'user__username',
    )
    list_display = (
        'user',
    )
    raw_id_fields = (
        'user',
    )
admin.site.register(ManagedUser, ManagedUserAdmin, site=AppAdminSite)
