from typing import List
from collections import OrderedDict
from rest_framework import serializers

from api.models import (
    AggregateActivity,
    Activity,
    User,
)
from api.utils.activity import ActivityUtils

class ActivityFCMDataSerializer(serializers.ModelSerializer):
    """
    Handles both push notifications and non-push activities.
    Activities must be a flat list for FCM
    """
    related_user_profile_picture_thumbnail = serializers.SerializerMethodField()
    related_user_username = serializers.CharField(max_length=150, required=False)
    related_image = serializers.CharField(max_length=600, required=False)
    related_comment_text = serializers.SerializerMethodField()
    push_notification_type = serializers.SerializerMethodField()

    def get_push_notification_type(self, activity: Activity):
        return 'activity'

    def get_related_user_profile_picture_thumbnail(self, activity: Activity):
        user: User = activity.related_user
        can_show =\
            user is not None and \
            user.is_active and \
            bool(user.profile_picture)
        return user.profile_picture.url if can_show else None

    def get_related_comment_text(self, activity) -> str | None:
        return ActivityUtils.related_comment_text(activity, replace_mention_ids=True)

    class Meta:
        model = Activity
        fields = (
            'push_notification_type',
            'id',
            'user',
            'type',
            'seen',
            'is_push',
            'created_at',
            'related_time',
            'related_user',
            'post',
            'comment',
            'related_comment',
            'experience',
            'playlist',
            'experience_stack',
            'related_user_username',
            'related_user_profile_picture_thumbnail',
            'follows_viewer',
            'followed_by_viewer',
            'related_image',
            'related_comment_text',
            'message',
        )

    def make_FCM_compatible(self, instance) -> List[OrderedDict]:
        '''
        Transforms Activity to representation needed for Firebase Messaging
        '''

        formatted_dict = self.to_representation(instance)

        fields = self._readable_fields

        for field in fields:
            for field in formatted_dict:
                if formatted_dict[field] is None:
                    formatted_dict[field] = ''
                elif type(formatted_dict[field]) != str :
                    formatted_dict[field] = str(formatted_dict[field])
        return formatted_dict


class AggregateActivitySerializer(ActivityFCMDataSerializer):

    # Related comment text is not used for aggregate activities
    class Meta:
        model = AggregateActivity
        fields = (
            'id',
            'user',
            'type',
            'count',
            'post',
            'comment',
            'related_comment',
            'experience',
            'playlist',
            'experience_stack',
            'created_at',
            'related_time',
            'related_user',
            'related_user_username',
            'related_user_profile_picture_thumbnail',
            'follows_viewer',
            'followed_by_viewer',
            'related_image',
            'message',
        )
