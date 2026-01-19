from rest_framework.serializers import SerializerMethodField

from api.serializers.experience import ExperienceViewSerializer
from schedules.models import ExperienceOfTheDaySchedule
from schedules.serializers.abstract import ScheduleSerializer

class ExperienceOfTheDayScheduleSerializer(ScheduleSerializer):
    experience = SerializerMethodField()
    def get_experience(self, eotds: ExperienceOfTheDaySchedule):
        serializer = ExperienceViewSerializer(
            instance=eotds.experience,
            context=self.context)
        return serializer.data

    class Meta(ScheduleSerializer.Meta):
        model = ExperienceOfTheDaySchedule
        fields = ScheduleSerializer.Meta.fields + (
            'experience',
        )

