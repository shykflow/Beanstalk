import json
from io import StringIO
from django.utils import timezone
from django.conf import settings
from django.core.management import call_command
from freezegun import freeze_time
from unittest.mock import patch

from schedules.models import (
    ExperienceOfTheDaySchedule,
)
from api.models import (
    Device,
    Experience,
    User,
)
from api.tests import SilenceableAPITestCase
from api.testing_overrides import (
    GlobalTestCredentials,
)

now = timezone.datetime(2022, 1, 20, tzinfo=timezone.utc)

class Test(SilenceableAPITestCase):
    experiences: list[Experience] = []
    old_schedules: list[ExperienceOfTheDaySchedule] = []
    upcoming_schedules: list[ExperienceOfTheDaySchedule] = []
    current_schedule: ExperienceOfTheDaySchedule
    user_allows_push_notif: User
    user_disallows_push_notif: User

    @freeze_time(now)
    def setUpTestData():
        Test.user_allows_push_notif = User.objects.create(
            username='allow',
            email='allow@email.com',
            email_verified=True)
        Test.user_disallows_push_notif = User.objects.create(
            username='disallow',
            email='disallow@email.com',
            email_verified=True,
            exp_of_the_day_push_pref=False)

        now = timezone.now()
        stale_timedelta = settings.STALE_DEVICE_THRESHOLD + timezone.timedelta(days=1)

        allow_pushes:list[bool] = [True, False]
        last_check_ins:list[timezone.datetime] = [now, now-stale_timedelta]
        offsets:list[None|int] = [
            None,
            0*60,
            6*60,
            9*60,
            12*60,
        ]
        for permission in allow_pushes:
            if permission:
                user = Test.user_allows_push_notif
            else:
                user = Test.user_disallows_push_notif
            for last_check_in in last_check_ins:
                for offset in offsets:
                    device = Device.objects.create(
                        user=user,
                        token=f'{permission}|{last_check_in}|{offset}',
                        minutes_offset=offset)
                    # auto_add_now=True means this needs to be set here.
                    device.last_check_in=last_check_in
                    device.save()


    @freeze_time(now)
    def test_no_exp_today(self):
        with patch('firebase_admin.messaging.send') as mock_method:
            experience = Experience.objects.create(
                created_by=GlobalTestCredentials.user,
                name=f'Exp 3 days ago')
            ExperienceOfTheDaySchedule.objects.create(
                publish_at=now - timezone.timedelta(days=3),
                notify_all_users=True,
                experience=experience)
            call_command('send_experience_of_the_day_notifs')
            self.assertEqual(mock_method.call_count, 0)

    @freeze_time(now)
    def test_exp_today(self):
        with patch('firebase_admin.messaging.send') as mock_method:
            experience = Experience.objects.create(
                created_by=GlobalTestCredentials.user,
                name=f'Exp today')
            ExperienceOfTheDaySchedule.objects.create(
                publish_at=now,
                notify_all_users=True,
                experience=experience)
            call_command('send_experience_of_the_day_notifs')
            self.assertEqual(mock_method.call_count, 1)

    @freeze_time(timezone.datetime(2023, 5, 21, 9, 1, tzinfo=timezone.utc))
    def test_9am_greenwich_publish_at_1am_sends(self):
        now = timezone.now()
        experience = Experience.objects.create(
            created_by=GlobalTestCredentials.user,
            name=f'Exp today at 1 am')
        ExperienceOfTheDaySchedule.objects.create(
            publish_at=now - timezone.timedelta(hours=8),
            notify_all_users=True,
            experience=experience)
        expected_results = [
            {'offset': -2*60, 'sent': False},
            {'offset': -1*60, 'sent': False},
            {'offset': 0*60, 'sent': True},
            {'offset': 1*60, 'sent': False},
            {'offset': 2*60, 'sent': False},
        ]
        device = Device.objects.create(
            user=Test.user_allows_push_notif,
            token='test_9am_greenwich_publish_at_1am')
        # auto_add_now=True means this needs to be set here.
        device.last_check_in=now-timezone.timedelta(hours=1)
        device.save()
        for expected in expected_results:
            offset = expected['offset']
            device.minutes_offset = offset
            device.save()
            # with freeze_time(dt + timezone.timedelta(minutes=expected['offset'])):
            with patch('firebase_admin.messaging.send') as mock_method:
                call_command('send_experience_of_the_day_notifs')
                self.assertEqual(
                    mock_method.call_count,
                    1 if expected['sent'] else 0,
                    msg=f'offset={offset}')

    @freeze_time(timezone.datetime(2023, 6, 26, 13, 1, tzinfo=timezone.utc))
    def test_9am_florida_publish_at_2am_sends(self):
        now = timezone.now()
        experience = Experience.objects.create(
            created_by=GlobalTestCredentials.user,
            name=f'Exp today at 2 am')
        ExperienceOfTheDaySchedule.objects.create(
            publish_at=now - timezone.timedelta(hours=11),
            notify_all_users=True,
            experience=experience)
        expected_results = [
            {'offset': -6*60, 'sent': False},
            {'offset': -5*60, 'sent': False},
            {'offset': -4*60, 'sent': True},
            {'offset': -3*60, 'sent': False},
            {'offset': -2*60, 'sent': False},
        ]
        device = Device.objects.create(
            user=Test.user_allows_push_notif,
            token='test_9am_florida_publish_at_2am')
        # auto_add_now=True means this needs to be set here.
        device.last_check_in=now-timezone.timedelta(hours=1)
        device.save()
        for expected in expected_results:
            offset = expected['offset']
            device.minutes_offset = offset
            device.save()
            # with freeze_time(dt + timezone.timedelta(minutes=expected['offset'])):
            with patch('firebase_admin.messaging.send') as mock_method:
                call_command('send_experience_of_the_day_notifs')
                self.assertEqual(
                    mock_method.call_count,
                    1 if expected['sent'] else 0,
                    msg=f'offset={offset}')

    @freeze_time(timezone.datetime(2023, 7, 13, 16, 1, tzinfo=timezone.utc))
    def test_9am_california_publish_at_midnight_sends(self):
        now = timezone.now()
        experience = Experience.objects.create(
            created_by=GlobalTestCredentials.user,
            name=f'Exp today at 12 am')
        ExperienceOfTheDaySchedule.objects.create(
            publish_at=now - timezone.timedelta(hours=16, minutes=1),
            notify_all_users=True,
            experience=experience)
        expected_results = [
            {'offset': -9*60, 'sent': False},
            {'offset': -8*60, 'sent': False},
            {'offset': -7*60, 'sent': True},
            {'offset': -6*60, 'sent': False},
            {'offset': -5*60, 'sent': False},
        ]
        device = Device.objects.create(
            user=Test.user_allows_push_notif,
            token='test_9am_california_publish_at_midnight')
        # auto_add_now=True means this needs to be set here.
        device.last_check_in=now-timezone.timedelta(hours=1)
        device.save()
        for expected in expected_results:
            offset = expected['offset']
            device.minutes_offset = offset
            device.save()
            # with freeze_time(dt + timezone.timedelta(minutes=expected['offset'])):
            with patch('firebase_admin.messaging.send') as mock_method:
                call_command('send_experience_of_the_day_notifs')
                self.assertEqual(
                    mock_method.call_count,
                    1 if expected['sent'] else 0,
                    msg=f'offset={offset}')
    
    @freeze_time(timezone.datetime(2023, 8, 5, 2, 1, tzinfo=timezone.utc))
    def test_9am_thailand_publish_at_9am_sends(self):
        now = timezone.now()
        experience = Experience.objects.create(
            created_by=GlobalTestCredentials.user,
            name=f'Exp today at 9 am')
        ExperienceOfTheDaySchedule.objects.create(
            publish_at=now - timezone.timedelta(minutes=1) + timezone.timedelta(hours=7), # - timezone.timedelta(days=1),
            notify_all_users=True,
            experience=experience)
        expected_results = [
            {'offset': 5*60, 'sent': False},
            {'offset': 6*60, 'sent': False},
            {'offset': 7*60, 'sent': True},
            {'offset': 8*60, 'sent': False},
            {'offset': 9*60, 'sent': False},
        ]
        device = Device.objects.create(
            user=Test.user_allows_push_notif,
            token='test_9am_thailand_publish_at_9am')
        # auto_add_now=True means this needs to be set here.
        device.last_check_in=now-timezone.timedelta(hours=1)
        device.save()
        for expected in expected_results:
            offset = expected['offset']
            device.minutes_offset = offset
            device.save()
            # with freeze_time(dt + timezone.timedelta(minutes=expected['offset'])):
            with patch('firebase_admin.messaging.send') as mock_method:
                call_command('send_experience_of_the_day_notifs')
                self.assertEqual(
                    mock_method.call_count,
                    1 if expected['sent'] else 0,
                    msg=f'offset={offset}')

    @freeze_time(timezone.datetime(2023, 5, 21, 9, 1, tzinfo=timezone.utc))
    def test_9am_greenwich_publish_at_11am_does_not_send(self):
        now = timezone.now()
        experience = Experience.objects.create(
            created_by=GlobalTestCredentials.user,
            name=f'Exp today at 11 am')
        ExperienceOfTheDaySchedule.objects.create(
            publish_at=now + timezone.timedelta(hours=2),
            notify_all_users=True,
            experience=experience)
        expected_results = [
            {'offset': -2*60, 'sent': False},
            {'offset': -1*60, 'sent': False},
            {'offset': 0*60, 'sent': False}, # Local Greenwich offset, currently 9 am
            {'offset': 1*60, 'sent': False},
            {'offset': 2*60, 'sent': False}, # 11 am somewhere else
            {'offset': 3*60, 'sent': False},
        ]
        device = Device.objects.create(
            user=Test.user_allows_push_notif,
            token='test_9am_greenwich_publish_at_11am_does_not_send')
        # auto_add_now=True means this needs to be set here.
        device.last_check_in=now-timezone.timedelta(hours=1)
        device.save()
        for expected in expected_results:
            offset = expected['offset']
            device.minutes_offset = offset
            device.save()
            # with freeze_time(dt + timezone.timedelta(minutes=expected['offset'])):
            with patch('firebase_admin.messaging.send') as mock_method:
                call_command('send_experience_of_the_day_notifs')
                self.assertEqual(
                    mock_method.call_count,
                    1 if expected['sent'] else 0,
                    msg=f'offset={offset}')

    @freeze_time(timezone.datetime(2023, 6, 26, 13, 1, tzinfo=timezone.utc))
    def test_9am_florida_publish_at_2pm_does_not_send(self):
        now = timezone.now()
        experience = Experience.objects.create(
            created_by=GlobalTestCredentials.user,
            name=f'Exp today at 2 pm')
        ExperienceOfTheDaySchedule.objects.create(
            publish_at=now + timezone.timedelta(hours=1),
            notify_all_users=True,
            experience=experience)
        expected_results = [
            {'offset': -6*60, 'sent': False},
            {'offset': -5*60, 'sent': False},
            {'offset': -4*60, 'sent': False}, # Local Florida offset, currently 9 am
            {'offset': -3*60, 'sent': False},
            {'offset': -2*60, 'sent': False},
            {'offset': -1*60, 'sent': False},
            {'offset': 0*60, 'sent': False},
            {'offset': 1*60, 'sent': False}, # 2 pm somewhere else
            {'offset': 2*60, 'sent': False},
        ]
        device = Device.objects.create(
            user=Test.user_allows_push_notif,
            token='test_9am_florida_publish_at_2pm_does_not_send')
        # auto_add_now=True means this needs to be set here.
        device.last_check_in=now-timezone.timedelta(hours=1)
        device.save()
        for expected in expected_results:
            offset = expected['offset']
            device.minutes_offset = offset
            device.save()
            # with freeze_time(dt + timezone.timedelta(minutes=expected['offset'])):
            with patch('firebase_admin.messaging.send') as mock_method:
                call_command('send_experience_of_the_day_notifs')
                self.assertEqual(
                    mock_method.call_count,
                    1 if expected['sent'] else 0,
                    msg=f'offset={offset}')

    @freeze_time(timezone.datetime(2023, 7, 13, 16, 1, tzinfo=timezone.utc))
    def test_9am_california_publish_at_10am_does_not_send(self):
        now = timezone.now()
        experience = Experience.objects.create(
            created_by=GlobalTestCredentials.user,
            name=f'Exp today at 10 am')
        ExperienceOfTheDaySchedule.objects.create(
            publish_at=now - timezone.timedelta(hours=6, minutes=1),
            notify_all_users=True,
            experience=experience)
        expected_results = [
            {'offset': -9*60, 'sent': False},
            {'offset': -8*60, 'sent': False},
            {'offset': -7*60, 'sent': False}, # Local California offset, currently 9am
            {'offset': -6*60, 'sent': False}, # 10am somewhere else
            {'offset': -5*60, 'sent': False},
        ]
        device = Device.objects.create(
            user=Test.user_allows_push_notif,
            token='test_9am_california_publish_at_10am_does_not_send')
        # auto_add_now=True means this needs to be set here.
        device.last_check_in=now-timezone.timedelta(hours=1)
        device.save()
        for expected in expected_results:
            offset = expected['offset']
            device.minutes_offset = offset
            device.save()
            # with freeze_time(dt + timezone.timedelta(minutes=expected['offset'])):
            with patch('firebase_admin.messaging.send') as mock_method:
                call_command('send_experience_of_the_day_notifs')
                self.assertEqual(
                    mock_method.call_count,
                    1 if expected['sent'] else 0,
                    msg=f'offset={offset}')
    
    @freeze_time(timezone.datetime(2023, 8, 5, 2, 1, tzinfo=timezone.utc))
    def test_9am_thailand_publish_at_3pm_does_not_send(self):
        now = timezone.now()
        experience = Experience.objects.create(
            created_by=GlobalTestCredentials.user,
            name=f'Exp today at 3 pm')
        ExperienceOfTheDaySchedule.objects.create(
            publish_at=now - timezone.timedelta(minutes=1) + timezone.timedelta(hours=13), # - timezone.timedelta(days=1),
            notify_all_users=True,
            experience=experience)
        expected_results = [
            {'offset': 5*60, 'sent': False},
            {'offset': 6*60, 'sent': False},
            {'offset': 7*60, 'sent': False}, # Local Thailand offset, currently 9am
            {'offset': 8*60, 'sent': False},
            {'offset': 9*60, 'sent': False},
            {'offset': 10*60, 'sent': False},
            {'offset': 11*60, 'sent': False},
            {'offset': 12*60, 'sent': False},
            {'offset': 13*60, 'sent': False}, # 3pm somewhere
            {'offset': 14*60, 'sent': False},
        ]
        device = Device.objects.create(
            user=Test.user_allows_push_notif,
            token='test_9am_thailand_publish_at_3pm_does_not_send')
        # auto_add_now=True means this needs to be set here.
        device.last_check_in=now-timezone.timedelta(hours=1)
        device.save()
        for expected in expected_results:
            offset = expected['offset']
            device.minutes_offset = offset
            device.save()
            # with freeze_time(dt + timezone.timedelta(minutes=expected['offset'])):
            with patch('firebase_admin.messaging.send') as mock_method:
                call_command('send_experience_of_the_day_notifs')
                self.assertEqual(
                    mock_method.call_count,
                    1 if expected['sent'] else 0,
                    msg=f'offset={offset}')

