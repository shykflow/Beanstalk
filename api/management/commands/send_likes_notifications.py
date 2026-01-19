import logging

from django.core.management.base import BaseCommand
from api.enums import ActivityType
from api.models.activity import Activity

from api.services.firebase import FirebaseService

logger = logging.getLogger('app')
firebase = FirebaseService()
like_types = (
    ActivityType.LIKED_EXPERIENCE,
    ActivityType.LIKED_PLAYLIST,
    ActivityType.LIKED_EXPERIENCE_STACK,
    ActivityType.LIKED_POST,
    ActivityType.LIKED_COMMENT,
)

class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("Running python manage.py send_likes_notifications")
        try:
            activity_dict = {}
            post_likes = Activity.objects.filter(
                seen=False,
                is_push=True,
                has_pushed=False,
                type__in=like_types)\
                    .prefetch_related('user')

            # Group activities by type, user, and, content
            key: str
            for activity in post_likes:
                match ActivityType(int(activity.type)):
                    case ActivityType.LIKED_POST:
                        key = f'{activity.type}-{activity.post}'
                    case ActivityType.LIKED_COMMENT:
                        key = f'{activity.type}-{activity.comment}'
                    case ActivityType.LIKED_PLAYLIST:
                        key = f'{activity.type}-{activity.playlist}'
                    case ActivityType.LIKED_EXPERIENCE:
                        key = f'{activity.type}-{activity.experience}'
                    case ActivityType.LIKED_EXPERIENCE_STACK:
                        key = f'{activity.type}-{activity.experience_stack}'
                    case _:
                        raise Exception()
                if activity_dict.get(key) is None :
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

            Activity.objects.bulk_update(post_likes, ['has_pushed'])
        except Exception as e:
            logger.info(str(e))
