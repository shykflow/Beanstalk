from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import (
    ExperienceStack,
)


class UserFollowedInline(admin.TabularInline):
    raw_id_fields = ('user',)
    model = ExperienceStack.users_followed.through
    extra = 0
    verbose_name_plural = "Follows"


class ExperienceInline(admin.TabularInline):
    raw_id_fields = ('experience',)
    model = ExperienceStack.experiences.through
    extra = 0
    verbose_name_plural = "Experiences"


class ExperienceStackAdmin(admin.ModelAdmin):
    list_display = ('name', 'description',)
    fields = ('name', 'description',)
    inlines = (UserFollowedInline, ExperienceInline,)
# Uncomment the following line if we plan on using ExperienceStack
# admin.site.register(ExperienceStack, ExperienceStackAdmin, site=AppAdminSite)
