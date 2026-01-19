import json
from rest_framework import status
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from api.models import (
    Experience,
    Playlist,
    Post,
    User,
    UserFollow,
)
from api.testing_overrides import GlobalTestCredentials, LifeFrameCategoryOverrides, TestFiles
from api.views.for_you_feed import ForYouCategories
from lf_service.models import Category
from . import disable_logging, SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    other_user: User
    other_user_token: Token
    endpoint_url = '/for_you_feed/'

    def setUpTestData():
        global_user: User = GlobalTestCredentials.user
        popular_category: Category
        popular_category = LifeFrameCategoryOverrides.popular['categories'][0]
        Test.other_user = User.objects.create(
            username='other',
            email='other@email.com',
            email_verified=True)
        Test.other_user_token = Token.objects.create(user=Test.other_user)
        UserFollow.objects.create(
            user=global_user,
            followed_user=Test.other_user)
        pl: Playlist = Playlist.objects.create(
            name='pl',
            created_by=Test.other_user)
        Experience.objects.create(
            name='exp',
            created_by=Test.other_user,
            categories=[popular_category.id])
        Post.objects.create(
            name='post',
            text='post text',
            created_by=Test.other_user)
        pl.update_aggregated_categories()


    def setUp(self):
        super().setUp()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {GlobalTestCredentials.token}')

    def test_for_you_categories_set_relevant(self):
        categories = ForYouCategories()
        # Set 2 , 1 duplicate
        categories.set_relevant([
            LifeFrameCategoryOverrides.relevant['categories'][0],
            LifeFrameCategoryOverrides.relevant['categories'][1],
            LifeFrameCategoryOverrides.relevant['categories'][1],
        ])
        self.assertEqual(len(categories.relevant), 2)
        self.assertEqual(len(categories.relevant_or_popular), 2)
        for item in [
                LifeFrameCategoryOverrides.relevant['categories'][0],
                LifeFrameCategoryOverrides.relevant['categories'][1],
            ]:
            self.assertTrue(item in categories.relevant)
        for item in [
                LifeFrameCategoryOverrides.relevant['categories'][0],
                LifeFrameCategoryOverrides.relevant['categories'][1],
            ]:
            self.assertTrue(item in categories.relevant_or_popular)
        # Set 1, no duplicate
        categories.set_relevant([
            LifeFrameCategoryOverrides.relevant['categories'][0],
        ])
        self.assertEqual(len(categories.relevant), 1)
        self.assertEqual(len(categories.relevant_or_popular), 1)
        for item in [
                LifeFrameCategoryOverrides.relevant['categories'][0],
            ]:
            self.assertTrue(item in categories.relevant)
        for item in [
                LifeFrameCategoryOverrides.relevant['categories'][0],
            ]:
            self.assertTrue(item in categories.relevant_or_popular)

    def test_for_you_categories_set_popular(self):
        categories = ForYouCategories()
        # Set 2 , 1 duplicate
        categories.set_popular([
            LifeFrameCategoryOverrides.popular['categories'][0],
            LifeFrameCategoryOverrides.popular['categories'][1],
            LifeFrameCategoryOverrides.popular['categories'][1],
        ])
        self.assertEqual(len(categories.popular), 2)
        self.assertEqual(len(categories.relevant_or_popular), 2)
        for item in [
                LifeFrameCategoryOverrides.popular['categories'][0],
                LifeFrameCategoryOverrides.popular['categories'][1],
            ]:
            self.assertTrue(item in categories.popular)
        for item in [
                LifeFrameCategoryOverrides.popular['categories'][0],
                LifeFrameCategoryOverrides.popular['categories'][1],
            ]:
            self.assertTrue(item in categories.relevant_or_popular)
        # Set 1, no duplicate
        categories.set_popular([
            LifeFrameCategoryOverrides.popular['categories'][0],
        ])
        self.assertEqual(len(categories.popular), 1)
        self.assertEqual(len(categories.relevant_or_popular), 1)
        for item in [
                LifeFrameCategoryOverrides.popular['categories'][0],
            ]:
            self.assertTrue(item in categories.popular)
        for item in [
                LifeFrameCategoryOverrides.popular['categories'][0],
            ]:
            self.assertTrue(item in categories.relevant_or_popular)

    def test_for_you_categories_add_relevant_and_popular(self):
        categories = ForYouCategories()
        categories.set_relevant([
            LifeFrameCategoryOverrides.relevant['categories'][0],
        ])
        categories.set_popular([
            LifeFrameCategoryOverrides.popular['categories'][0],
        ])
        self.assertEqual(len(categories.relevant), 1)
        self.assertEqual(len(categories.popular), 1)
        self.assertEqual(len(categories.relevant_or_popular), 2)

    def test_response_shape(self):
        for mode in ['follow', 'global']:
            endpoint = f"{Test.endpoint_url}?mode={mode}"
            response = self.client.get(endpoint)
            response_data: dict[str, any] = response.data
            must_return_fields = [
                'continuation',
                'items',
            ]
            for field in must_return_fields:
                self.assertTrue(
                    field in response_data,
                    msg=f'Field {field} is not in response data')
            continuation = response_data['continuation']
            items = response_data['items']
            self.assertTrue(type(continuation) is str,
                msg=f'mode={mode}, type(continuation) is not str')
            self.assertTrue(len(continuation) > 0,
                msg=f'mode={mode}, len(continuation) <= 0')
            self.assertTrue(type(items) is list,
                msg=f'mode={mode}, type(items) is not list')

    def test_types_filter_all(self):
        self._test_types_filter(
            query_params='?mode=global&types=experiences,lists,posts',
            expected = {
                'Experience': True,
                'Playlist': True,
                'Post': True,
            })
        self._test_types_filter(
            query_params='',
            expected = {
                'Experience': True,
                'Playlist': True,
                'Post': True,
            })

    def test_types_filter_experiences_only(self):
        self._test_types_filter(
            query_params='?mode=global&types=experiences',
            expected = {
                'Experience': True,
                'Playlist': False,
                'Post': False,
            })

    def test_types_filter_lists_only(self):
        self._test_types_filter(
            query_params='?mode=global&types=lists',
            expected = {
                'Experience': False,
                'Playlist': True,
                'Post': False,
            })

    def test_types_filter_posts_only(self):
        self._test_types_filter(
            query_params='?mode=global&types=posts',
            expected = {
                'Experience': False,
                'Playlist': False,
                'Post': True,
            })

    def _test_types_filter(self, query_params: str, expected: dict[str, bool]):
        response = self.client.get(f'{Test.endpoint_url}{query_params}')
        response_data: dict[str, any] = response.data
        found = {
            'Experience': False,
            'Playlist': False,
            'Post': False,
        }
        for item in response_data['items']:
            found[item['model']] = True
        for key in found:
            msg = f'\n{key}\n  Expected: {expected[key]}\n  Found: {found[key]}'
            self.assertEqual(
                found[key],
                expected[key],
                msg=msg)

    def test_video_only(self):
        other_user_client = APIClient()
        other_user_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {Test.other_user_token}')
        data = {
            'highlight_image': TestFiles.get_simple_uploaded_file('jpg'),
            'highlight_image_thumbnail': TestFiles.get_simple_uploaded_file('jpg'),
            'video': TestFiles.get_simple_uploaded_file('mp4'),
            'json': json.dumps({
                'name': 'name',
                'description': 'test description',
            }),
        }
        response = other_user_client.post('/experiences/', data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        data = {
            'highlight_image': TestFiles.get_simple_uploaded_file('jpg'),
            'highlight_image_thumbnail': TestFiles.get_simple_uploaded_file('jpg'),
            'video': TestFiles.get_simple_uploaded_file('mp4'),
            'json': json.dumps({
                'name': 'name',
                'description': 'test description',
            }),
        }
        response = other_user_client.post('/playlists/', data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        data = {
            'highlight_image': TestFiles.get_simple_uploaded_file('jpg'),
            'highlight_image_thumbnail': TestFiles.get_simple_uploaded_file('jpg'),
            'video': TestFiles.get_simple_uploaded_file('mp4'),
            'json': json.dumps({
                'name': 'name',
                'text': 'test description',
            }),
        }
        response = other_user_client.post('/posts/', data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        query_params='?mode=global&types=experiences,lists,posts'
        response = self.client.get(f'{Test.endpoint_url}{query_params}')
        response_data: dict[str, any] = response.data
        self.assertEqual(len(response_data['items']), 6)

        query_params='?mode=global&types=experiences,lists,posts&video_only=true'
        response = self.client.get(f'{Test.endpoint_url}{query_params}')
        response_data: dict[str, any] = response.data
        self.assertEqual(len(response_data['items']), 3)