import logging

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import (
    Q,
    QuerySet,
)

from api.services.firebase import FirebaseService
from api.models import (
    Device,
    Experience,
    User,
)
from schedules.models import ExperienceOfTheDaySchedule

logger = logging.getLogger('app')
firebase = FirebaseService()

class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("Running python manage.py send_experience_of_the_day_notifs")
        now_utc = timezone.now()
        midnight_utc = timezone.datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
        nine_am_utc = timezone.datetime(now_utc.year, now_utc.month, now_utc.day, 9, tzinfo=timezone.utc)
        stale_threshold = (now_utc - timezone.timedelta(days=30*3)).date()
        notify_at_offset = 9 * 60
        current_hour = now_utc.hour
        current_minute_offset = current_hour * 60

        experience_otd: Experience
        eotd_schedule = ExperienceOfTheDaySchedule.objects \
            .filter(publish_at__range=[midnight_utc, nine_am_utc]) \
            .filter(notify_all_users=True) \
            .first()

        if eotd_schedule is None:
            logger.info("No exp of the day schedule found")
            return
        experience_otd = eotd_schedule.experience


        users_qs: QuerySet[User] = User.objects \
            .filter(exp_of_the_day_push_pref=True)
        devices_qs: QuerySet[Device] = Device.objects \
            .filter(user__in=users_qs) \
            .exclude(last_check_in__lt=stale_threshold) \
            .exclude(minutes_offset__isnull=True) \
            .filter(minutes_offset=notify_at_offset-current_minute_offset)
        fb_service = FirebaseService()
        for device in devices_qs:
            title = 'New experience of the day!'

            message_body = experience_otd.name

            data_dict = {
                'push_notification_type': 'experience_of_the_day',
                # 'related_image': experience_image_url,
                # 'experience': experience_id,
            }
            fb_service.send_message_to_device(device, title, message_body, data_dict)

