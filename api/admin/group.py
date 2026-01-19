from django import forms
from django.contrib import admin
from django.contrib.admin import widgets
from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe

from api.admin.admin_site import AppAdminSite

from api.models import (
    User,
)

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        # Django Admin requires either "fields" or "exclude"
        # See the "fieldsets" of the main Admin class to see
        # what fields are included.
        exclude = tuple()
        widgets = {
            'permissions': widgets.FilteredSelectMultiple(
                verbose_name='permissions',
                is_stacked=False),
        }


class GroupAdmin(admin.ModelAdmin):
    form = GroupForm
    fields = (
        'name',
        'permissions',
        # 'users_in_group',
    )
    def users_in_group(self, group: Group):
        users: list[User] = list(group.user_set.all())
        html = ''
        if len(users) == 0:
            html = 'No users'
        else:
            html = '''
                <ul style="margin: 0; padding: 0;">
            '''
            for user in users:
                html += f'''
                    <li>{user.username} | {user.email}</li>
                '''
            html += '''
                </ul>
            '''
        return mark_safe(html)

admin.site.register(Group, GroupAdmin, site=AppAdminSite)
