from django.contrib import admin

from api.admin.admin_site import AppAdminSite
from api.models.task_result import TaskResult

class TaskResultAdmin(admin.ModelAdmin):
    list_display = ("user", "task_id", "text", "status", "created_at")
admin.site.register(TaskResult, TaskResultAdmin, site=AppAdminSite)