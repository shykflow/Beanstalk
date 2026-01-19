from rest_framework import serializers

from api.models import BadgePlan
from api.serializers.badge import BadgeSerializer


class BadgePlanSerializer(serializers.ModelSerializer):

    badge = BadgeSerializer()

    class Meta:
        model = BadgePlan
        fields = (
            'id',
            'type',
            'earn_until',
            'earn_limit',
            'experience',
            'badge',
        )
