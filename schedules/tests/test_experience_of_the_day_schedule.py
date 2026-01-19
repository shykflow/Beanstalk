from django.utils import timezone
from freezegun import freeze_time
from rest_framework import status

from schedules.models import (
    ExperienceOfTheDaySchedule,
)
from api.models import (
    Experience,
)
from api.tests import SilenceableAPITestCase
from api.testing_overrides import (
    GlobalTestCredentials,
)

now = timezone.datetime(2022, 1, 20, tzinfo=timezone.utc)

class Test(SilenceableAPITestCase):
    experiences: list[Experience] = []
    old_schedules: list[ExperienceOfTheDaySchedule] = []
    upcoming_schedules: list[ExperienceOfTheDaySchedule] = []
    current_schedule: ExperienceOfTheDaySchedule

    @freeze_time(now)
    def setUpTestData():
        now = timezone.datetime.now(tz=timezone.utc)

        # 5 days back
        for i in range(5):
            publish_at = now - timezone.timedelta(days=5-i)
            experience = Experience.objects.create(
                created_by=GlobalTestCredentials.user,
                name=f'Exp {i+1} back')
            Test.experiences.append(experience)
            schedule = ExperienceOfTheDaySchedule.objects.create(
                publish_at=publish_at,
                experience=experience)
            Test.old_schedules.append(schedule)

        # today
        experience = Experience.objects.create(
            created_by=GlobalTestCredentials.user,
            name=f'Exp today')
        Test.experiences.append(experience)
        Test.current_schedule = ExperienceOfTheDaySchedule.objects.create(
            publish_at=now,
            experience=experience)

        # 5 days forward
        for i in range(5):
            publish_at = now + timezone.timedelta(days=i+1)
            experience = Experience.objects.create(
                created_by=GlobalTestCredentials.user,
                name=f'Exp {i+1} forward')
            Test.experiences.append(experience)
            schedule = ExperienceOfTheDaySchedule.objects.create(
                publish_at=publish_at,
                experience=experience)
            Test.upcoming_schedules.append(schedule)


    def setUp(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {GlobalTestCredentials.token}')


    @freeze_time(now + timezone.timedelta(hours=12))
    def test_response_shape(self):
        page_size = 5
        endpoint = '/experience_of_the_day_schedules/' + \
            f'?page_size={page_size}' + \
            '&minutes_offset=0'
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_dict: dict = response.data
        self.assertIn('count', response_dict)
        self.assertIn('next_page', response_dict)
        self.assertIn('previous_page', response_dict)
        self.assertIn('results', response_dict)
        results = response_dict['results']
        self.assertTrue(len(results), page_size)


    @freeze_time(now + timezone.timedelta(hours=12))
    def test_list_no_minutes_offset(self):
        page_size = 5
        endpoint = '/experience_of_the_day_schedules/' + \
            f'?page_size={page_size}' + \
            '&minutes_offset=0'
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_dict: dict = response.data
        results: list[dict] = response_dict['results']
        self.assertTrue(len(results), page_size)
        self.assertEqual(results[0]['id'], Test.current_schedule.id)
        result_ids: list[int] = [x['id'] for x in results]
        expected_ids: list[int] = [
            Test.current_schedule.id,
            Test.old_schedules[-1].id,
            Test.old_schedules[-2].id,
            Test.old_schedules[-3].id,
            Test.old_schedules[-4].id,
        ]
        for i in range(len(expected_ids)):
            self.assertTrue(
                result_ids[i] == expected_ids[i],
                msg=f"At index {i}")


    @freeze_time(now + timezone.timedelta(hours=12))
    def test_list_with_minutes_offset_negative(self):
        # Note, 720 minutes in 12 hours, shifting behind utc,
        # should get yesterday's current first
        page_size = 5
        endpoint = '/experience_of_the_day_schedules/' + \
            f'?page_size={page_size}' + \
            '&minutes_offset=-721'
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_dict: dict = response.data
        results: list[dict] = response_dict['results']
        self.assertTrue(len(results), page_size)
        self.assertEqual(results[0]['id'], Test.old_schedules[-1].id)
        result_ids: list[int] = [x['id'] for x in results]
        expected_ids: list[int] = [
            Test.old_schedules[-1].id,
            Test.old_schedules[-2].id,
            Test.old_schedules[-3].id,
            Test.old_schedules[-4].id,
            Test.old_schedules[-5].id,
        ]
        for i in range(len(expected_ids)):
            self.assertTrue(
                result_ids[i] == expected_ids[i],
                msg=f"At index {i}")


    @freeze_time(now + timezone.timedelta(hours=12))
    def test_list_with_minutes_offset_positive(self):
        # Note, 720 minutes in 12 hours, shifting ahead of utc,
        # should get tomorrow's current first
        page_size = 5
        endpoint = '/experience_of_the_day_schedules/' + \
            f'?page_size={page_size}' + \
            '&minutes_offset=721'
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_dict: dict = response.data
        results: list[dict] = response_dict['results']
        result_ids: list[int] = [x['id'] for x in results]
        expected_ids: list[int] = [
            Test.upcoming_schedules[0].id,
            Test.current_schedule.id,
            Test.old_schedules[-1].id,
            Test.old_schedules[-2].id,
            Test.old_schedules[-3].id,
        ]
        for i in range(len(expected_ids)):
            self.assertTrue(
                result_ids[i] == expected_ids[i],
                msg=f"At index {i}")


    @freeze_time(now + timezone.timedelta(hours=12))
    def test_current_no_minutes_offset(self):
        endpoint = '/experience_of_the_day_schedules/current/' + \
            '?minutes_offset=0'
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_dict: dict = response.data
        self.assertIn('id', response_dict)
        self.assertIn('experience', response_dict)
        self.assertEqual(response_dict['id'], Test.current_schedule.id)


    @freeze_time(now + timezone.timedelta(hours=12))
    def test_current_with_minutes_offset_negative(self):
        # Note, 720 minutes in 12 hours, shifting behind utc,
        # should get yesterday's current
        endpoint = '/experience_of_the_day_schedules/current/' + \
            '?minutes_offset=-721'
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_dict: dict = response.data
        self.assertIn('id', response_dict)
        self.assertIn('experience', response_dict)
        self.assertEqual(
            response_dict['id'],
            Test.old_schedules[-1].id)


    @freeze_time(now + timezone.timedelta(hours=12))
    def test_current_with_minutes_offset_positive(self):
        # Note, 720 minutes in 12 hours, shifting ahead of utc,
        # should get tomorrow's current
        endpoint = '/experience_of_the_day_schedules/current/' + \
            '?minutes_offset=721'
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_dict: dict = response.data
        self.assertIn('id', response_dict)
        self.assertIn('experience', response_dict)
        self.assertEqual(
            response_dict['id'],
            Test.upcoming_schedules[0].id)


    # Shift the date forward in time so today is 1 day past the test's pre-built
    # "upcoming" schedules.
    @freeze_time(now + timezone.timedelta(days=6))
    def test_current_no_schedule_today(self):
        # Create an experience for tomorrow, make sure it does not come back
        # as the current
        now = timezone.datetime.now(tz=timezone.utc)
        experience = Experience.objects.create(
            created_by=GlobalTestCredentials.user,
            name=f'Exp tomorrow')
        ExperienceOfTheDaySchedule.objects.create(
            publish_at=now + timezone.timedelta(days=1),
            experience=experience)

        endpoint = '/experience_of_the_day_schedules/current/' + \
            '?minutes_offset=0'
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_dict: dict = response.data
        self.assertIsNone(response_dict)


    @freeze_time(now + timezone.timedelta(days=12))
    def test_current_deleted_exp(self):
        now = timezone.datetime.now(tz=timezone.utc)
        experience = Experience.objects.create(
            created_by=GlobalTestCredentials.user,
            name=f'Exp will delete')
        ExperienceOfTheDaySchedule.objects.create(
            publish_at=now,
            experience=experience)
        experience.delete()
        endpoint = '/experience_of_the_day_schedules/current/' + \
            '?minutes_offset=0'
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_dict: dict = response.data
        self.assertIsNone(response_dict)


    @freeze_time(now + timezone.timedelta(days=12))
    def test_list_deleted_exp(self):
        now = timezone.datetime.now(tz=timezone.utc)
        experience = Experience.objects.create(
            created_by=GlobalTestCredentials.user,
            name=f'Exp will delete')
        eotds = ExperienceOfTheDaySchedule.objects.create(
            publish_at=now,
            experience=experience)
        experience.delete()
        page_size = 5
        endpoint = '/experience_of_the_day_schedules/' + \
            f'?page_size={page_size}' + \
            '&minutes_offset=0'
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_dict: dict = response.data
        results: list[dict] = response_dict['results']
        result_ids: list[int] = [x['id'] for x in results]
        self.assertNotIn(eotds.id, result_ids)
