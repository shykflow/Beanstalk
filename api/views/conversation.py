import json
from django.http import Http404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from django.conf import settings

from api.enums import CustomHttpStatusCodes
from api.models import User
from api.models.user_follow import UserFollow
from api.serializers.conversations import CreateConversationSerializer
from api.serializers.user import UserIdSerializer
from api.services.sendbird import Sendbird
import sendbird_platform_sdk
from sendbird_platform_sdk.models import SendBirdGroupChannel


class ConversationViewSet(
        viewsets.GenericViewSet,
        viewsets.mixins.ListModelMixin):

    @action(detail=False, methods=["get"])
    def sendbird_application_id(self, request: Request, *args, **kwargs) -> Response:
        return Response(settings.SENDBIRD_APPLICATION_ID)

    def post(self, request: Request, *args, **kwargs) -> Response:
        id_serializer = CreateConversationSerializer(data=request.data)
        id_serializer.is_valid(raise_exception=True)
        user_dicts = request.data.get('users')
        # Conversations must contain the user
        # Do not make duplicate conversations
        user_ids = []
        for user_dict in user_dicts:
            user_ids.append(user_dict.get('id'))
        convo_users: User = User.objects.filter(pk__in=user_ids).all()
        contains_user = False
        request_user = request.user
        for user in convo_users:
            # Must be email verified
            if not user.email_verified:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            if request_user == user:
                contains_user = True
            else:
                if user.blocks.contains(request_user):
                    return Response(
                        status=CustomHttpStatusCodes.HTTP_485_USER_BLOCKED_YOU)
                if request_user.blocks.contains(user):
                    return Response(
                        status=CustomHttpStatusCodes.HTTP_486_YOU_BLOCKED_USER)
        if not contains_user:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Ensure users who do not follow are sent conversation requests
        # TODO: Consider refactoring to this, it is shorter and should already be distinct:
        #   followers = request.user.followed_by.filter(.....)
        followers = UserFollow.objects \
            .filter(followed_user=request.user.id, user__in=user_ids) \
            .distinct("user")
        joined_users = []
        invited_users = []
        sendBird = Sendbird()
        for user in convo_users:
            is_following = False
            if user == request.user:
                continue
            for follow in followers:
                if (follow.user.id == user.id):
                    joined_users.append(user)
                    is_following = True
                    break
            if not is_following:
                invited_users.append(user)
        channel_url = sendBird.create_channel(
            request.user,
            invited_users,
            joined_users,
            request.data.get('is_group_chat'))
        return Response(channel_url)

    # @action(detail=True, methods=['delete'])
    # def delete(self, request: Request, pk, *args, **kwargs) -> Response:
    #     sendBird = Sendbird()
    #     channel = sendBird.get_channel(pk)
    #     # Conversation must be a group chat, not DMs
    #     if (channel.is_distinct):
    #         return Response(status=status.HTTP_400_BAD_REQUEST)
    #     sendBird.delete_channel(pk)
    #     return Response(status=status.HTTP_204_NO_CONTENT)

    # @action(detail=True, methods=['post'])
    # def add_users(self, request: Request, pk) -> Response:
    #     sendbird = Sendbird()
    #     validation_serializer = UserIdSerializer(data=request.data, many=True)
    #     validation_serializer.is_valid(raise_exception=True)
    #     conversation: SendBirdGroupChannel
    #     try:
    #         conversation = sendbird.get_channel(pk)
    #     except sendbird_platform_sdk.ApiException as e:
    #         # channel not found
    #         if json.loads(e.body)['code'] == 400201:
    #             raise Http404
    #         else:
    #             raise e
    #     # Conversation must be a group chat, not DMs
    #     if conversation.is_distinct:
    #         return Response(status=status.HTTP_400_BAD_REQUEST)
    #     user_dicts = request.data
    #     user_ids = []
    #     for user_dict in user_dicts:
    #         user_ids.append(user_dict.get('id'))
    #     convo_users: User = User.objects.filter(pk__in=user_ids).all()
    #     sendbird.add_participant(pk, convo_users)
    #     serializer = UserIdSerializer(convo_users, many=True)
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)

    # @action(detail=True, methods=['delete'])
    # def remove_users(self, request: Request, pk) -> Response:
    #     sendbird = Sendbird()
    #     validation_serializer = UserIdSerializer(data=request.data, many=True)
    #     validation_serializer.is_valid(raise_exception=True)
    #     user_dicts = request.data
    #     user_ids = []
    #     for user_dict in user_dicts:
    #         user_ids.append(str(user_dict.get('id')) )
    #     sendbird = Sendbird()
    #     try:
    #         conversation = sendbird.get_channel(pk)
    #     except sendbird_platform_sdk.ApiException as e:
    #         # channel not found
    #         if json.loads(e.body)['code'] == 400201:
    #             raise Http404
    #         else:
    #             raise e
    #     # Conversation must be a group chat, not DMs
    #     if (conversation.is_distinct):
    #         return Response(status=status.HTTP_400_BAD_REQUEST)
    #     sendbird.remove_participants(pk, user_ids)
    #     return Response(status=status.HTTP_204_NO_CONTENT)
