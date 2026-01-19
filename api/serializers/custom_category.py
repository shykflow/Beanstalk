import logging

from rest_framework import serializers

from api.models import (
    CustomCategory,
)

logger = logging.getLogger('app')

class CustomCategoryViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomCategory
        fields = (
            'id',
            'name',
            'experience_count',
            'playlist_count',
            'post_count',
        )
