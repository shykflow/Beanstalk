from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models import Experience
from schedules.models import ExperienceOfTheDaySchedule

class ExperienceOfTheDayScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'experience',
        'created_by',
        'publish_at',
        'experience_is_soft_deleted',
        'notify_all_users',
    )
    raw_id_fields = (
        'experience',
    )
    search_fields = (
        'experience__name',
        'experience__created_by__username',
    )

    @admin.display(
        ordering='experience__created_by__username',
        description='Created by')
    def created_by(self, eotds: ExperienceOfTheDaySchedule):
        exp: Experience = eotds.experience
        return exp.created_by

    @admin.display(
        boolean=True,
        ordering='experience__is_deleted',
        description='Experience is soft deleted')
    def experience_is_soft_deleted(self, eotds: ExperienceOfTheDaySchedule):
        exp: Experience = eotds.experience
        return exp.is_deleted

admin.site.register(ExperienceOfTheDaySchedule, ExperienceOfTheDayScheduleAdmin, site=AppAdminSite)
