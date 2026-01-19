import datetime

from firebase_admin import messaging, initialize_app
from firebase_admin.exceptions import NotFoundError
from django.conf import settings

from api.models import (
    Device,
    User,
)
from api.models.activity import Activity
from api.serializers.activity import ActivityFCMDataSerializer
from api.utils.activity import ActivityUtils

class FirebaseService():

    def __new__(self):
        if not hasattr(self, 'instance'):
            self.instance = super(FirebaseService, self).__new__(self)
            self.app = initialize_app()

        return self.instance

    def get_details(self, token):
        return

    def send_message_to_topic(self, topic:str, title:str, body:str, data_dict:dict={}):
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data_dict,
            topic=topic)
        messaging.send(msg, app=self.app)

    def send_message_to_device(
        self,
        device:Device,
        title:str,
        body:str,
        data_dict:dict={}):
        stale_threshold = (datetime.datetime.now() - settings.STALE_DEVICE_THRESHOLD).date()
        if device.last_check_in < stale_threshold:
            return
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data_dict,
            token=device.token)
        try:
            messaging.send(msg, app=self.app)
        except NotFoundError as e:
            # Firebase could not find the device by the token provided
            device.delete()
            print(f'deleted device {device} for user ${device.user.id}')


    def send_message_to_user_devices(
        self,
        user:User,
        title:str,
        body:str,
        data_dict:dict={}):
        stale_threshold = (datetime.datetime.now() - settings.STALE_DEVICE_THRESHOLD).date()
        devices: list[Device] = Device.objects \
            .filter(user=user) \
            .filter(last_check_in__gt=stale_threshold)
        for device in devices:
            msg = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data_dict,
                token=device.token)
            try:
                messaging.send(msg, app=self.app)
            except NotFoundError as e:
                # Firebase could not find the device by the token provided
                device.delete()
                print(f'deleted device for user ${user.id}')

    def push_activity_to_user(self, activity:Activity, similar_item_count: int = 1):
        user: User = activity.user
        if not user.activity_push_pref \
            or not user.mention_push_pref and activity.is_tag_type \
            or not user.like_push_pref and activity.is_like_type \
            or not user.comment_push_pref and activity.is_comment_type \
            or not user.accept_complete_push_pref and activity.is_content_interaction_type \
            or not user.follow_push_pref and activity.is_follow_type:
            return
        title = ActivityUtils.get_activity_message(activity, item_count=similar_item_count)
        body = None
        if ActivityUtils.comment_type(activity):
            # Push notifications should show mentions as usernames, not <@123> in preview text
            body = ActivityUtils.related_comment_text(activity, replace_mention_ids=True)

        devices: list[Device] = Device.objects.filter(user=user)
        data_serializer = ActivityFCMDataSerializer(activity)
        data_dict = data_serializer.make_FCM_compatible(activity)
        stale_threshold = (datetime.datetime.now() - settings.STALE_DEVICE_THRESHOLD).date()
        for device in devices:
            if device.last_check_in < stale_threshold:
                continue
            msg = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data_dict,
                token=device.token)
            try:
                messaging.send(msg, app=self.app)
            except NotFoundError as e:
                # Firebase could not find the device by the token provided
                device.delete()
                print(f'deleted device for user ${user.id}')
