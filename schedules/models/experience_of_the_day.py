from django.db.models import (
    BooleanField,
    CASCADE,
    ForeignKey,
)

from schedules.models.abstract import Schedule

class ExperienceOfTheDaySchedule(Schedule):
    experience = ForeignKey('api.Experience', on_delete=CASCADE)
    notify_all_users = BooleanField(
        default=False,
        help_text='If true, all users will be notified when this ' \
            'experience goes live or at 9 am, whichever is later.')
