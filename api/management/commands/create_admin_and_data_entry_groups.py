import logging
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

logger = logging.getLogger('app')


class Command(BaseCommand):
    admin_perms = [
        # 'add_logentry',
        # 'change_logentry',
        # 'delete_logentry',
        'view_logentry',

        # 'add_permission',
        # 'change_permission',
        # 'delete_permission',
        'view_permission',

        # 'add_group',
        # 'change_group',
        # 'delete_group',
        'view_group',

        # 'add_contenttype',
        # 'change_contenttype',
        # 'delete_contenttype',
        # 'view_contenttype',

        # 'add_session',
        # 'change_session',
        # 'delete_session',
        # 'view_session',

        # 'add_token',
        # 'change_token',
        # 'delete_token',
        # 'view_token',

        # 'add_tokenproxy',
        # 'change_tokenproxy',
        # 'delete_tokenproxy',
        # 'view_tokenproxy',

        'add_user',
        'change_user',
        # 'delete_user',
        'view_user',

        'add_badge',
        'change_badge',
        # 'delete_badge',
        'view_badge',

        'add_badgetemplate',
        'change_badgetemplate',
        # 'delete_badgetemplate',
        'view_badgetemplate',

        'add_playlist',
        'change_playlist',
        # 'delete_playlist',
        'view_playlist',

        'add_categorymapping',
        'change_categorymapping',
        'delete_categorymapping',
        'view_categorymapping',

        'add_experience',
        'change_experience',
        # 'delete_experience',
        'view_experience',

        'add_experiencestack',
        'change_experiencestack',
        # 'delete_experiencestack',
        'view_experiencestack',

        'add_comment',
        'change_comment',
        # 'delete_comment',
        'view_comment',

        # 'add_milestone',
        # 'change_milestone',
        # 'delete_milestone',
        # 'view_milestone',

        # 'add_showcase',
        # 'change_showcase',
        # # 'delete_showcase',
        # 'view_showcase',

        # 'add_usersettings',
        # 'change_usersettings',
        # 'delete_usersettings',
        'view_usersettings',

        # 'add_powerprofileadmin',
        # 'change_powerprofileadmin',
        # # 'delete_powerprofileadmin',
        # 'view_powerprofileadmin',

        'add_post',
        'change_post',
        # 'delete_post',
        'view_post',

        # 'add_notification',
        # 'change_notification',
        # 'delete_notification',
        'view_notification',

        # 'add_interest',
        # 'change_interest',
        # 'delete_interest',
        'view_interest',

        # 'add_earnedbadge',
        # 'change_earnedbadge',
        # 'delete_earnedbadge',
        # 'view_earnedbadge',

        # 'add_device',
        # 'change_device',
        # 'delete_device',
        'view_device',

        # 'add_experiencesponsorship',
        # 'change_experiencesponsorship',
        # # 'delete_experiencesponsorship',
        # 'view_experiencesponsorship',

        # 'add_experiencecompletion',
        # 'change_experiencecompletion',
        # 'delete_experiencecompletion',
        # 'view_experiencecompletion',

        'add_playlistuser',
        'change_playlistuser',
        'delete_playlistuser',
        'view_playlistuser',

        # 'add_playlistsponsorship',
        # 'change_playlistsponsorship',
        # # 'delete_playlistsponsorship',
        # 'view_playlistsponsorship',

        'add_playlistexperience',
        'change_playlistexperience',
        'delete_playlistexperience',
        'view_playlistexperience',

        'add_badgeplan',
        'change_badgeplan',
        # 'delete_badgeplan',
        'view_badgeplan',

        # 'add_aggregatenotification',
        # 'change_aggregatenotification',
        # 'delete_aggregatenotification',
        'view_aggregatenotification',

        # 'add_experiencestarrating',
        # 'change_experiencestarrating',
        # 'delete_experiencestarrating',
        'view_experiencestarrating',

        # 'add_experiencecostrating',
        # 'change_experiencecostrating',
        # 'delete_experiencecostrating',
        'view_experiencecostrating',

        # 'add_playliststarrating',
        # 'change_playliststarrating',
        # 'delete_playliststarrating',
        'view_playliststarrating',

        # 'add_userfollow',
        # 'change_userfollow',
        # 'delete_userfollow',
        'view_userfollow',

        # 'add_report',
        'change_report',
        # 'delete_report',
        'view_report',

        'add_attachment',
        'change_attachment',
        'delete_attachment',
        'view_attachment',
    ]

    data_entry_perms = [
        # 'add_logentry',
        # 'change_logentry',
        # 'delete_logentry',
        # 'view_logentry',

        # 'add_permission',
        # 'change_permission',
        # 'delete_permission',
        # 'view_permission',

        # 'add_group',
        # 'change_group',
        # 'delete_group',
        # 'view_group',

        # 'add_contenttype',
        # 'change_contenttype',
        # 'delete_contenttype',
        # 'view_contenttype',

        # 'add_session',
        # 'change_session',
        # 'delete_session',
        # 'view_session',

        # 'add_token',
        # 'change_token',
        # 'delete_token',
        # 'view_token',

        # 'add_tokenproxy',
        # 'change_tokenproxy',
        # 'delete_tokenproxy',
        # 'view_tokenproxy',

        # 'add_user',
        # 'change_user',
        # 'delete_user',
        'view_user',

        'add_badge',
        'change_badge',
        # 'delete_badge',
        'view_badge',

        'add_badgetemplate',
        'change_badgetemplate',
        # 'delete_badgetemplate',
        'view_badgetemplate',

        'add_playlist',
        'change_playlist',
        # 'delete_playlist',
        'view_playlist',

        'add_categorymapping',
        'change_categorymapping',
        'delete_categorymapping',
        'view_categorymapping',

        'add_experience',
        'change_experience',
        # 'delete_experience',
        'view_experience',

        # 'add_experiencestack',
        # 'change_experiencestack',
        # 'delete_experiencestack',
        # 'view_experiencestack',

        # 'add_comment',
        # 'change_comment',
        # 'delete_comment',
        'view_comment',

        # 'add_milestone',
        # 'change_milestone',
        # 'delete_milestone',
        # 'view_milestone',

        # 'add_showcase',
        # 'change_showcase',
        # 'delete_showcase',
        # 'view_showcase',

        # 'add_usersettings',
        # 'change_usersettings',
        # 'delete_usersettings',
        # 'view_usersettings',

        # 'add_powerprofileadmin',
        # 'change_powerprofileadmin',
        # 'delete_powerprofileadmin',
        # 'view_powerprofileadmin',

        # 'add_post',
        # 'change_post',
        # 'delete_post',
        # 'view_post',

        # 'add_notification',
        # 'change_notification',
        # 'delete_notification',
        # 'view_notification',

        # 'add_interest',
        # 'change_interest',
        # 'delete_interest',
        # 'view_interest',

        # 'add_earnedbadge',
        # 'change_earnedbadge',
        # 'delete_earnedbadge',
        # 'view_earnedbadge',

        # 'add_device',
        # 'change_device',
        # 'delete_device',
        # 'view_device',

        # 'add_experiencesponsorship',
        # 'change_experiencesponsorship',
        # 'delete_experiencesponsorship',
        # 'view_experiencesponsorship',

        # 'add_experiencecompletion',
        # 'change_experiencecompletion',
        # 'delete_experiencecompletion',
        # 'view_experiencecompletion',

        # 'add_playlistuser',
        # 'change_playlistuser',
        # 'delete_playlistuser',
        # 'view_playlistuser',

        # 'add_playlistsponsorship',
        # 'change_playlistsponsorship',
        # 'delete_playlistsponsorship',
        # 'view_playlistsponsorship',

        'add_playlistexperience',
        'change_playlistexperience',
        'delete_playlistexperience',
        'view_playlistexperience',

        'add_badgeplan',
        'change_badgeplan',
        # 'delete_badgeplan',
        'view_badgeplan',

        # 'add_aggregatenotification',
        # 'change_aggregatenotification',
        # 'delete_aggregatenotification',
        # 'view_aggregatenotification',

        # 'add_experiencestarrating',
        # 'change_experiencestarrating',
        # 'delete_experiencestarrating',
        # 'view_experiencestarrating',

        # 'add_playliststarrating',
        # 'change_playliststarrating',
        # 'delete_playliststarrating',
        # 'view_playliststarrating',

        # 'add_userfollow',
        # 'change_userfollow',
        # 'delete_userfollow',
        # 'view_userfollow',

        'add_attachment',
        'change_attachment',
        'delete_attachment',
        'view_attachment',
    ]

    def handle(self, *args, **options):
        logger.info('Running python manage.py create_admin_and_data_entry_groups')
        self.create_admin_group()
        self.create_data_entry_group()
        # Note: In development, the seed command generates the admin and data_entry users.
        # They get lifeframe IDs and some generated content. This is to make sure those
        # users are still valid users of the platform.


    def create_admin_group(self):
        group, created = Group.objects.get_or_create(name='Admin')
        if not created:
            group.permissions.clear()
        for codename in Command.admin_perms:
            permission = Permission.objects.filter(codename=codename).first()
            if permission is None:
                continue
            group.permissions.add(permission)


    def create_data_entry_group(self):
        group, created = Group.objects.get_or_create(name='Data Entry')
        if not created:
            group.permissions.clear()
        for codename in Command.data_entry_perms:
            permission = Permission.objects.filter(codename=codename).first()
            if permission is None:
                continue
            group.permissions.add(permission)
