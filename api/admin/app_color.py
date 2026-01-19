from django import forms
from django.contrib import admin
from django.forms.widgets import TextInput

from api.admin.admin_site import AppAdminSite
from api.models import AppColor

class AppColorForm(forms.ModelForm):
    class Meta:
        model = AppColor
        fields = '__all__'
        widgets = {
            'color': TextInput(attrs={'type': 'color'}),
        }


class AppColorAdmin(admin.ModelAdmin):
    form = AppColorForm
    list_display = ('color', 'admin_preview',)
    readonly_fields = ('admin_preview',)
admin.site.register(AppColor, AppColorAdmin, site=AppAdminSite)
