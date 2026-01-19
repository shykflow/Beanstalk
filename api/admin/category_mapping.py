from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django import forms
from django.utils.safestring import mark_safe

from api.admin.admin_site import AppAdminSite
from api.models import (
    CategoryMapping,
)
from lf_service.category import (
    LifeFrameCategoryService,
)
from django.contrib.admin import widgets

class _SponsorshipRawIdWidget(widgets.ForeignKeyRawIdWidget):
    def url_parameters(self):
        res = super(_SponsorshipRawIdWidget, self).url_parameters()
        object: CategoryMapping = self.attrs.get('object', None)
        if object:
            # Filter variants by product_id
            res['category_id'] = object.category_id
        return res



class SponsoredFilter(SimpleListFilter):
    title = 'Sponsored'
    parameter_name = 'sponsorship'
    def lookups(self, request, model_admin):
        return (
            ('true', 'Sponsored'),
            ('false', 'Not sponsored'),
        )
    def queryset(self, request, queryset):
        value = self.value()
        if value == 'true':
            return queryset.filter(sponsorship__isnull=False)
        elif value == 'false':
            return queryset.filter(sponsorship__isnull=True)
        return queryset

class ShownInPickerFilter(SimpleListFilter):
    title = 'Shown In Picker'
    parameter_name = 'show_in_picker'
    def lookups(self, request, model_admin):
        return (
            ('true', 'Shown in picker'),
            ('false', 'Not shown in picker'),
        )
    def queryset(self, request, queryset):
        value = self.value()
        if value == 'true':
            return queryset.filter(show_in_picker=True)
        elif value == 'false':
            return queryset.filter(show_in_picker=False)
        return queryset

class CategoryMappingForm(forms.ModelForm):

    class Meta:
        model = CategoryMapping
        # Django Admin requires either "fields" or "exclude"
        # See the "fieldsets" of the main Admin class to see
        # what fields are included.
        exclude = tuple()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mapping: CategoryMapping = kwargs.get('instance', None)
        exists_in_db = mapping is not None and mapping.pk is not None

        self.fields['sponsorship'].help_text = ' '.join([
            '<h3>SAVE THIS CATEGORY MAPPING BEFORE SETTING A SPONSORSHIP</h3>' if not exists_in_db else '',
            'When selecting, sponsorships will be filtered to have the same category_id as',
            f'this Category Mapping',
            f'(category id <span style="font-weight: bold">{mapping.category_id if exists_in_db else "UNKNOWN"}</span>)',
        ]).strip()

        if exists_in_db:
            field = mapping._meta.get_field('sponsorship')
            self.fields['sponsorship'].widget = _SponsorshipRawIdWidget(
                rel=field.remote_field,
                admin_site=admin.site,
                # Pass the object to attrs
                attrs={'object': mapping})

    def clean_category_id(self):
        category_id = self.cleaned_data['category_id']
        if 'category_id' not in self.changed_data:
            return category_id
        # Make sure category is a real category
        lf_category_service = LifeFrameCategoryService()
        try:
            lf_category_service.retrieve(category_id)
        except:
            raise forms.ValidationError('This ID does not exist in Life Frame')
        return category_id



class CategoryMappingAdmin(admin.ModelAdmin):
    list_per_page = 10
    form = CategoryMappingForm
    search_fields = (
        'category_id',
        'sponsorship__user__username',
        'sponsorship__user__email',
    )
    list_filter = (
        'show_in_picker',
    )
    fieldsets = (
        (None, {
            'fields': (
                'admin_name',
                'category_id',
                'show_in_picker',
                'picker_sequence',
                'image',
                'details',
                'overlay_opacity',
                'text_color',
                'background_color',
                'admin_image',
                'admin_text_color',
                'admin_background_color',
                'admin_preview',
            ),
        }),
        ('Sponsorship', {
            'fields': (
                'sponsorship',
                'admin_sponsorship_status_large',
                'admin_sponsorship_info',
            ),
        }),
    )
    list_display = (
        'category_id',
        'admin_name',
        'admin_preview',
        # 'admin_text_color',
        # 'admin_background_color',
        # 'admin_image',
        'show_in_picker',
        'picker_sequence',
        '_sponsorship',
        'admin_sponsorship_status_small',
    )
    raw_id_fields = (
        'sponsorship',
    )
    readonly_fields = (
        'admin_name',
        'admin_preview',
        'admin_text_color',
        'admin_background_color',
        'admin_image',
        'admin_sponsorship_status_small',
        'admin_sponsorship_status_large',
        'admin_sponsorship_info',
    )
    list_filter = (
        SponsoredFilter,
        ShownInPickerFilter,
    )
    def _sponsorship(self, cm: CategoryMapping):
        if cm.sponsorship is None:
            return None
        expires_at_str = None
        if cm.sponsorship.expires_at is not None:
            expires_at_str = cm.sponsorship.expires_at.strftime('%a %d %b %Y, %I:%M%p') + ' UTC'
        details = [
            f'@{cm.sponsorship.user.username}',
        ]
        if expires_at_str is not None:
            details.append(expires_at_str)
        details_html = ''.join([f'<li>{x}</li>' for x in details])
        html = f"""
            <ul style="list-style-type: none;">
                {details_html}
            </ul>
        """
        return mark_safe(html)
    _sponsorship.admin_order_field = 'sponsorship__user__username'

admin.site.register(CategoryMapping, CategoryMappingAdmin, site=AppAdminSite)
