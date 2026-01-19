from rest_framework import serializers

from api.serializers.post import PostValidationSerializer


class CompletionSerializer(serializers.Serializer):
    post = PostValidationSerializer(required=False)
    minutes_offset = serializers.IntegerField(max_value=1440, min_value=-1440)
