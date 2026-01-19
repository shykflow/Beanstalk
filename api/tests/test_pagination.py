from django.conf import settings
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.authtoken.models import Token

from api.models import (
    Playlist,
    Experience,
    User
)
from . import disable_logging, SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    user: User
    playlist: Playlist
    total_count: int
    token: Token

    def setUpTestData():
        Test.user = User.objects.create(
            username = 'test_user',
            email = 'testuserone@email.com',
            email_verified = True)
        Test.playlist = Playlist.objects.create(
            name='test_playlist',
            created_by=Test.user)
        Test.total_count = 50
        playlists_to_create = []
        experiences_to_create: list[Experience] = []
        for i in range(Test.total_count):
            experiences_to_create.append(
                Experience(
                    name=f"test_playlist_{i}",
                    created_by=Test.user))
            if i == 0:
                # Skip creating first playlist since it's already created
                continue
            playlists_to_create.append(
                Playlist(
                    name=f"test_playlist_{i}",
                    created_by=Test.user))
        experiences: QuerySet[Experience] = Experience.objects.bulk_create(experiences_to_create)
        Playlist.objects.bulk_create(playlists_to_create)
        Test.playlist.experiences.add(*experiences)
        Test.token = Token.objects.create(user=Test.user)


    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')


    def test_experience_pagination(self):
        # GET without specifying a page size should get 10
        response = self.client.get('/experiences/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], Test.total_count)
        self.assertEqual(response.data['next_page'], 2)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIsNone(response.data['previous_page'])

        # GET specifying a valid page size should return the valid page size
        response = self.client.get(f'/experiences/?page_size={Test.total_count}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], Test.total_count)
        self.assertEqual(len(response.data['results']), Test.total_count)
        self.assertIsNone(response.data['previous_page'])
        self.assertIsNone(response.data['next_page'])


    def test_playlist_pagination(self):
        # GET without specifying a page size should get 20
        response = self.client.get('/playlists/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], Test.total_count)
        self.assertEqual(response.data['next_page'], 2)
        self.assertEqual(len(response.data['results']), 20)
        self.assertIsNone(response.data['previous_page'])

        # GET specifying a valid page size should return the valid page size
        response = self.client.get(f'/playlists/?page_size={Test.total_count}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], Test.total_count)
        self.assertEqual(len(response.data['results']), Test.total_count)
        self.assertIsNone(response.data['previous_page'])
        self.assertIsNone(response.data['next_page'])


    def test_playlist_experiences_pagination(self):
        # GET without specifying a page size should get 10
        endpoint = f'/playlists/{Test.playlist.id}/experiences/'
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], Test.total_count)
        self.assertEqual(response.data['next_page'], 2)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIsNone(response.data['previous_page'])

        # GET specifying a valid page size should return the valid page size
        response = self.client.get(f'{endpoint}?page_size={Test.total_count}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], Test.total_count)
        self.assertEqual(len(response.data['results']), Test.total_count)
        self.assertIsNone(response.data['previous_page'])
        self.assertIsNone(response.data['next_page'])


    @disable_logging
    def test_invalid_pagination(self):
        too_large_page = settings.MAX_PAGINATION_PAGE_SIZE + 1
        with self.assertRaises(Exception):
            self.client.get('/experiences/?page_size=abc123')
        response = self.client.get('/experiences/?page_size=0')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.get('/experiences/?page_size=-1')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.get(f'/experiences/?page_size={too_large_page}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        with self.assertRaises(Exception):
            self.client.get('/playlists/?page_size=abc123')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.get('/playlists/?page_size=0')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.get('/playlists/?page_size=-1')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.get(f'/playlists/?page_size={too_large_page}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        endpoint = f'/playlists/{Test.playlist.id}/experiences/'
        with self.assertRaises(Exception):
            self.client.get(f'{endpoint}?page_size=abc123')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.get(f'{endpoint}?page_size=0')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.get(f'{endpoint}?page_size=-1')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.get(f'{endpoint}?page_size={too_large_page}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
