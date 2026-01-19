from django.conf import settings
from django.test import override_settings

from api.models import (
    Experience,
    Playlist,
    Post,
    User,
    UserFollow,
)
from api.testing_overrides import GlobalTestCredentials, LifeFrameCategoryOverrides
from lf_service.models import Category
from . import disable_logging, SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    other_user: User
    endpoint_url = '/discover_feed/'

    def setUpTestData():
        global_user: User = GlobalTestCredentials.user
        popular_category: Category
        popular_category = LifeFrameCategoryOverrides.popular['categories'][0]
        Test.other_user = User.objects.create(
            username='other',
            email='other@email.com',
            email_verified=True)
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


    def test_response_shape(self):
        _DISCOVER_QUERY_LIMITS: dict[str, int] = settings.DISCOVER_QUERY_LIMITS

        for categories_only in [True, False]:
            DISCOVER_QUERY_LIMITS = _DISCOVER_QUERY_LIMITS.copy()
            DISCOVER_QUERY_LIMITS['CATEGORIES_ONLY'] = categories_only
            with override_settings(DISCOVER_QUERY_LIMITS=DISCOVER_QUERY_LIMITS):
                response = self.client.get(Test.endpoint_url)
                response_data: dict[str, any] = response.data
                must_return_fields = [
                    'continuation',
                    'categories',
                    'experiences',
                    'playlists',
                    'posts',
                ]
                list_fields = [
                    'categories',
                    'experiences',
                    'playlists',
                    'posts',
                ]
                continuation = response_data['continuation']
                for field in must_return_fields:
                    self.assertTrue(
                        field in response_data,
                        msg=f'Field {field} is not in response data')
                for field in list_fields:
                    items = response_data[field]
                    self.assertTrue(type(continuation) is str,
                        msg=f'CATEGORIES_ONLY={categories_only}, type(continuation) is not str')
                    self.assertTrue(len(continuation) > 0,
                        msg=f'CATEGORIES_ONLY={categories_only}, len(continuation) <= 0')
                    self.assertTrue(type(items) is list,
                        msg=f'CATEGORIES_ONLY={categories_only}, type(items) is not list')
