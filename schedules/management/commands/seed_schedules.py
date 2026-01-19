from django.utils import timezone
from django.core.management.base import BaseCommand

from schedules.models import (
    ExperienceOfTheDaySchedule,
)
from api.models import (
    Experience,
    User,
)

class Command(BaseCommand):

    def get_random_user(self) -> User:
        return User.objects \
            .filter(email_verified=True) \
            .order_by('?') \
            .first()


    def handle(self, *args, **options):
        self.generate_experience_of_the_days()

    def generate_experience_of_the_days(self):
        print("Experience of the Days")
        now_date = timezone.datetime.now(tz=timezone.utc).date()
        now = timezone.datetime(
            now_date.year,
            now_date.month,
            now_date.day,
            tzinfo=timezone.utc)
        print('  Historical')
        for i in range(5):
            publish_at = now - timezone.timedelta(days=5-i)
            print(f'    {publish_at.date()}')
            if ExperienceOfTheDaySchedule.objects \
                .filter(publish_at=publish_at) \
                .exists():
                print(f'      Skipped - already exists')
                continue
            experience = Experience.objects \
                .exclude(highlight_image='') \
                .order_by('?') \
                .first()
            if experience is None:
                experience, created = Experience.objects.get_or_create(
                    created_by=self.get_random_user(),
                    name=f'Schedule Exp {i+1} back')
            ExperienceOfTheDaySchedule.objects.get_or_create(
                publish_at=publish_at,
                experience=experience)
            print(f'      Created')


        print('  Today')
        print(f'    {now.date()}')
        if ExperienceOfTheDaySchedule.objects \
            .filter(publish_at=now) \
            .exists():
            print(f'      Skipped - already exists')
        else:
            experience = Experience.objects \
                .exclude(highlight_image='') \
                .order_by('?') \
                .first()
            if experience is None:
                experience, created = Experience.objects.get_or_create(
                    created_by=self.get_random_user(),
                    name=f'Schedule Exp today')
            ExperienceOfTheDaySchedule.objects.get_or_create(
                publish_at=now,
                experience=experience)
            print(f'      Created')

        print('  Future')
        for i in range(5):
            publish_at = now + timezone.timedelta(days=i+1)
            print(f'    {publish_at.date()}')
            if ExperienceOfTheDaySchedule.objects \
                .filter(publish_at=publish_at) \
                .exists():
                print(f'      Skipped - already exists')
                continue
            experience = Experience.objects \
                .exclude(highlight_image='') \
                .order_by('?') \
                .first()
            if experience is None:
                experience, created = Experience.objects.get_or_create(
                    created_by=self.get_random_user(),
                    name=f'Schedule Exp {i+1} forward')
            ExperienceOfTheDaySchedule.objects.get_or_create(
                publish_at=publish_at,
                experience=experience)
            print(f'      Created')
