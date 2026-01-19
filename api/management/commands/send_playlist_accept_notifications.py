import logging

from django.core.management.base import BaseCommand
from api.enums import ActivityType
from api.models.activity import Activity

from api.services.firebase import FirebaseService

logger = logging.getLogger('app')
firebase = FirebaseService()


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            activity_dict = {}
            activities = Activity.objects.filter(
                seen=False,
                is_push=True,
                has_pushed=False,
                type=ActivityType.ACCEPTED_PLAYLIST)\
                    .prefetch_related('user')

            # Group activities by user and content
            key: str
            for activity in activities:
                key = f'{activity.playlist.id}'
                if activity_dict.get(key) is None:
                    activity_dict[key] = [activity]
                else:
                    activity_dict[key].append(activity)
                activity.has_pushed = True

            # Send each notification
            for grouped_activities in activity_dict.values():
                num_activities = len(grouped_activities)
                activity = grouped_activities[0]
                try:
                    firebase.instance.push_activity_to_user(activity, similar_item_count=num_activities)
                except Exception as e:
                    logger.info(str(e))

            Activity.objects.bulk_update(activities, ['has_pushed'])
        except Exception as e:
            logger.info(str(e))
