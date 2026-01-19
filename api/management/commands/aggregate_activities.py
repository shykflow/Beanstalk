import logging
from uuid import uuid4
from django.db.models import Q
from django.core.management.base import BaseCommand
from api.models import (
  Activity,
  AggregateActivity,
)

logger = logging.getLogger('app')


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info('Running python manage.py aggregate_activities')

        # TODO - Soft Deleting: {
        #   Make sure soft-deleted content does not have the related image attached,
        #   blank it out to null.
        # }

        # Group all unaggregated and seen activities for aggregation
        activities = Activity.objects.filter(aggregated=False, seen=True) \
            .order_by('created_at') \
            .prefetch_related('user')
        activity_dict = {}
        aggregate_query = Q()
        key: str
        for activity in activities:
            key = _activity_dict_key(activity)
            activity.aggregated = True
            if activity_dict.get(key) is None:
                # follow activities aren't aggregated. They always need a unique entry
                if activity.is_follow_type :
                    activity_dict[uuid4()] = [activity]
                    continue
                activity_dict[key] = [activity]
                aggregate_query = aggregate_query | Q(user=activity.user,
                        type=activity.type,
                        post=activity.post,
                        comment=activity.comment,
                        experience=activity.experience,
                        playlist=activity.playlist,
                        experience_stack=activity.experience_stack)
            else:
                activity_dict[key].append(activity)

        # retrieve all current Aggregate activities
        existing_aggregates = AggregateActivity.objects.all().filter(aggregate_query)
        new_aggregates : list[AggregateActivity] = []
        aggregates_dict = {}
        for agg in existing_aggregates:
            aggregates_dict[_activity_dict_key(agg)] = agg

        for grouped_activities in activity_dict.values():
            a : Activity = grouped_activities[0]
            num_activities = len(grouped_activities)
            existing_agg = aggregates_dict.get(_activity_dict_key(a))
            # update existing
            if existing_agg is not None:
                aggregates_dict[_activity_dict_key(a)].count += num_activities
                aggregates_dict[_activity_dict_key(a)].related_time = a.created_at
                aggregates_dict[_activity_dict_key(a)].related_user = a.related_user
            # create new
            else:
                new_aggregates.append(AggregateActivity(
                    user=a.user,
                    type=a.type,
                    related_user=a.related_user,
                    count=num_activities,
                    post=a.post,
                    comment=a.comment,
                    experience=a.experience,
                    playlist=a.playlist,
                    experience_stack=a.experience_stack))
        logger.info(f'Updating {existing_aggregates.count()} aggregate activities')
        logger.info(f'Creating {len(new_aggregates)} new aggregate activities')
        AggregateActivity.objects.bulk_create(new_aggregates)
        AggregateActivity.objects.bulk_update(
            aggregates_dict.values(),
            ['count','related_time','related_user'])
        Activity.objects.bulk_update(activities, ['aggregated'])
        logger.info(f'Successfully aggregated activities')



def _activity_dict_key(activity : Activity | AggregateActivity) -> str:
    return f'{activity.user}-{activity.type}-{activity.comment}-\
        {activity.experience}-{activity.playlist}-{activity.experience_stack}'
