from rest_framework import serializers

from api.models import Badge


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = (
            'id',
            'description',
            'name',
            'photo',
        )
