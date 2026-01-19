from rest_framework import serializers

class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        fields = (
            'id',
            'publish_at',
        )
