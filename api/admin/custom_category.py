from django.contrib import admin
from api.admin.abstract.soft_delete_model_admin import SoftDeleteTabularInlinePaginated

from api.admin.admin_site import AppAdminSite
from api.models import CustomCategory
from api.models import Experience


class ExperiencesInline(SoftDeleteTabularInlinePaginated):
    fields = ('experience',)
    raw_id_fields = ('experience',)
    model = Experience.custom_categories.through
    extra = 0
    verbose_name_plural = "experiences"


class CustomCategoryAdmin(admin.ModelAdmin):
    class Meta:
        verbose_name_plural = "categories"
    name = "categories"

    model = CustomCategory
    list_display = (
        'name',
        'needs_manual_review',
    )
    search_fields = (
        'name',
    )
    fields =  (
        'name',
        'needs_manual_review',
    )
    inlines = (
        ExperiencesInline,
    )
admin.site.register(CustomCategory, CustomCategoryAdmin, site=AppAdminSite)
