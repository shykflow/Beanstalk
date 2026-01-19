from django.utils import timezone


from api.models import (
    CategoryMapping,
    Experience,
    User,
)
from api.testing_overrides import (
    GlobalTestCredentials,
    LifeFrameCategoryOverrides,
)
from sponsorship.models import (
    CategorySponsorship,
)
from lf_service.category import (
    Category,
)
from api.tests import disable_logging, SilenceableAPITestCase

class Test(SilenceableAPITestCase):

    def setUpTestData():
        pass


    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {GlobalTestCredentials.token}')


    def test_category_mapping_shape_no_sponsorship(self):
        category: Category = LifeFrameCategoryOverrides.popular['categories'][0]
        mapping = CategoryMapping.objects.create(
            category_id=category.id,
            show_in_picker=True,
            background_color='#000000')
        endpoints = [
            f'/categories/{mapping.id}/',
            f'/categories/from_category_id/?id={category.id}',
        ]
        for endpoint in endpoints:
            endpoint = f'/categories/{mapping.id}/'
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            data = response.data
            self.assertEqual(data['category_id'],      mapping.category_id)
            self.assertEqual(data['show_in_picker'],   mapping.show_in_picker)
            self.assertEqual(data['text_color'],       mapping.text_color)
            self.assertEqual(data['background_color'], mapping.background_color)
            self.assertIsNone(data['sponsorship'])


    def test_category_mapping_shape_with_sponsorship(self):
        now = timezone.datetime.now(tz=timezone.utc)
        user: User = GlobalTestCredentials.user
        category: Category = LifeFrameCategoryOverrides.popular['categories'][0]
        experience = Experience.objects.create(
            created_by=user,
            name='exp',
            description='exp')
        sponsorship = CategorySponsorship.objects.create(
            user=user,
            category_id=category.id,
            experience_ids=[experience.id],
            expires_at=now + timezone.timedelta(days=3),
            details="Some extra details")
        mapping = CategoryMapping.objects.create(
            category_id=category.id,
            show_in_picker=True,
            background_color='#000000',
            sponsorship=sponsorship)
        endpoints = [
            f'/categories/{mapping.id}/',
            f'/categories/from_category_id/?id={category.id}',
        ]
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            data = response.data
            self.assertEqual(data['category_id'],      mapping.category_id)
            self.assertEqual(data['show_in_picker'],   mapping.show_in_picker)
            self.assertEqual(data['text_color'],       mapping.text_color)
            self.assertEqual(data['background_color'], mapping.background_color)
            self.assertIsNotNone(data['sponsorship'])
            sponsorship_dict: dict[str, any] = data['sponsorship']
            sponsorship_user_dict: dict[str, any] = sponsorship_dict['user']
            self.assertEqual(sponsorship_dict['id'],            sponsorship.id)
            self.assertEqual(sponsorship_dict['details'],       sponsorship.details)
            self.assertEqual(sponsorship_dict['image'],         sponsorship.image)
            self.assertEqual(sponsorship_user_dict['id'],       user.id)
            self.assertEqual(sponsorship_user_dict['username'], user.username)
            response_created_at_str: str = sponsorship_dict['created_at']
            response_created_at_str = response_created_at_str.replace('Z', '+00:00')
            response_created_at = timezone.datetime.fromisoformat(
                response_created_at_str)
            self.assertEqual(response_created_at, sponsorship.created_at)
            response_expires_at_str: str = sponsorship_dict['expires_at']
            response_expires_at_str = response_expires_at_str.replace('Z', '+00:00')
            response_expires_at = timezone.datetime.fromisoformat(
                response_expires_at_str)
            self.assertEqual(response_expires_at, sponsorship.expires_at)


    def test_sponsorship_expired_returns_none(self):
        now = timezone.datetime.now(tz=timezone.utc)
        user: User = GlobalTestCredentials.user
        category: Category = LifeFrameCategoryOverrides.popular['categories'][0]
        sponsorship = CategorySponsorship.objects.create(
            user=user,
            category_id=category.id,
            expires_at=now + timezone.timedelta(days=3),
            details="Some extra details")
        mapping = CategoryMapping.objects.create(
            category_id=category.id,
            show_in_picker=True,
            background_color='#000000',
            sponsorship=sponsorship)
        endpoints = [
            f'/categories/{mapping.id}/',
            f'/categories/from_category_id/?id={category.id}',
        ]
        for endpoint in endpoints:
            endpoint = f'/categories/{mapping.id}/'
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            sponsorship_dict = response.data['sponsorship']
            self.assertIsNotNone(sponsorship_dict)

        # Expire the sponsorship, should return None
        sponsorship.expires_at = now - timezone.timedelta(days=3)
        sponsorship.save()
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            sponsorship_dict = response.data['sponsorship']
            self.assertIsNone(sponsorship_dict)

    def test_sponsorship_mismatch_category_id_returns_none(self):
        now = timezone.datetime.now(tz=timezone.utc)
        user: User = GlobalTestCredentials.user
        category_1: Category = LifeFrameCategoryOverrides.popular['categories'][0]
        sponsorship = CategorySponsorship.objects.create(
            user=user,
            category_id=category_1.id,
            expires_at=now + timezone.timedelta(days=3),
            details="Some extra details")
        mapping = CategoryMapping.objects.create(
            category_id=category_1.id,
            show_in_picker=True,
            background_color='#000000',
            sponsorship=sponsorship)
        endpoints = [
            f'/categories/{mapping.id}/',
            f'/categories/from_category_id/?id={category_1.id}',
        ]
        for endpoint in endpoints:
            endpoint = f'/categories/{mapping.id}/'
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            sponsorship_dict = response.data['sponsorship']
            self.assertIsNotNone(sponsorship_dict)

        category_2: Category = LifeFrameCategoryOverrides.popular['categories'][1]
        # Make the categories mismatch
        sponsorship.category_id = category_2.id
        sponsorship.save()
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            sponsorship_dict = response.data['sponsorship']
            self.assertIsNone(sponsorship_dict)
