from django.contrib.auth import get_user_model
from rest_framework import serializers

from api.serializers.user import UserIdSerializer

class CreateConversationSerializer(serializers.Serializer):
    is_group_chat = serializers.BooleanField()
    users = UserIdSerializer
