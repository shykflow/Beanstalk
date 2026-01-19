from django.contrib import admin
from django import forms

from api.admin.admin_site import AppAdminSite
from api.models import NearYouMapping


class NearYouMappingForm(forms.ModelForm):
    class Meta:
        model = NearYouMapping
        fields = '__all__'

class NearYouMappingAdmin(admin.ModelAdmin):
    list_per_page = 10
    form = NearYouMappingForm
    fields = (
        'is_default',
        'latitude',
        'longitude',
        'radius',
        'image',
        'overlay_opacity',
        'text_color',
        'background_color',
        'admin_text_color',
        'admin_background_color',
        'admin_preview',
    )
    list_display = (
        '__str__',
        'admin_preview',
        'admin_text_color',
        'admin_background_color',
    )
    readonly_fields = (
        'admin_preview',
        'admin_text_color',
        'admin_background_color',
    )

admin.site.register(NearYouMapping, NearYouMappingAdmin, site=AppAdminSite)
