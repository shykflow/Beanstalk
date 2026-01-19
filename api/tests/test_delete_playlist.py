import datetime
import colorama

from rest_framework import status

from api.models import (
    Playlist,
    PlaylistAccept,
    PlaylistCompletion,
    PlaylistSave,
    User,
    UserFollow,
)
from api.testing_overrides import GlobalTestCredentials
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    playlist: Playlist
    followed_user: User

    def setUpTestData():
        Test.followed_user = User.objects.create(
            username = 'followed_user',
            email = 'followed_user@email.com',
            email_verified = True)

    def setUp(self):
        super().setUp()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {GlobalTestCredentials.token}')
        Test.playlist = Playlist.objects.create(
            name="Delete this",
            description="This is going to be soft deleted",
            created_by=GlobalTestCredentials.user)

    def test_soft_delete_happens(self):
        Test.playlist.delete()
        deleted_bl = Playlist.objects \
            .filter(pk=Test.playlist.pk) \
            .first()
        self.assertIsNone(deleted_bl)
        deleted_bl = Playlist.all_objects \
            .filter(pk=Test.playlist.pk) \
            .first()
        self.assertIsNotNone(deleted_bl)

    def test_retrieve_soft_deleted(self):
        response = self.client.get(f'/playlists/{Test.playlist.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        Test.playlist.delete()
        response = self.client.get(f'/playlists/{Test.playlist.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_soft_deleted_endpoint(self):
        response = self.client.get(f'/playlists/{Test.playlist.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.delete(f'/playlists/{Test.playlist.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(f'/playlists/{Test.playlist.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_action_page(self):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        url = f'/action/content_counts/'

        # Test initially created content from this class
        response = self.client.get(url)
        expectations = {
            # Accepted Count
            'experience_count': 0,
            # Accepted and not completed count
            'active_experience_count': 0,
            # Accepted and not completed count
            'completed_playlist_count': 0,
            # Total post count
            'post_count': 0,
            # roughly:
            # user.saved_experiences.count() + user.saved_playlists.count()
            'saved_for_later_count': 0,
            # Any Exp that has an ending time that's within a week
            'upcoming_experience_count': 0,
            # Any BL that has an ending time that's within a week
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # Accept the playlist created before this test at the top of the class
        PlaylistAccept.objects.create(
            user=GlobalTestCredentials.user,
            playlist=Test.playlist)
        response = self.client.get(url)
        expectations = {
            'experience_count': 0,
            'active_experience_count': 0,
            'completed_playlist_count': 0,
            'saved_for_later_count': 0,
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # Follow another user, no changes in the action page
        UserFollow.objects.create(
            user = GlobalTestCredentials.user,
            followed_user = Test.followed_user,
            created_at = now)
        response = self.client.get(url)
        expectations = {
            'experience_count': 0,
            'active_experience_count': 0,
            'completed_playlist_count': 0,
            'saved_for_later_count': 0,
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # Accept a playlist created by this followed user
        followed_user_playlist: Playlist = Playlist.objects.create(
            name="Followed user created this",
            description="This is going to be soft deleted",
            created_by=Test.followed_user)
        PlaylistAccept.objects.create(
            user=Test.followed_user,
            playlist=followed_user_playlist)
        response = self.client.get(url)
        expectations = {
            'experience_count': 0,
            'active_experience_count': 0,
            'completed_playlist_count': 0,
            'saved_for_later_count': 0,
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # global user accepts, and saves a playlist
        playlist_2: Playlist = Playlist.objects.create(
            name="Global user created this",
            description="This is going to be soft deleted",
            created_by=GlobalTestCredentials.user,
            end_time=now + datetime.timedelta(hours=6))
        PlaylistAccept.objects.create(
            user=GlobalTestCredentials.user,
            playlist=playlist_2)
        PlaylistSave.objects.create(
            user=GlobalTestCredentials.user,
            playlist=playlist_2)
        response = self.client.get(url)
        expectations = {
            'experience_count': 0,
            'active_experience_count': 0,
            'completed_playlist_count': 0,
            'saved_for_later_count': 1,
            'upcoming_playlist_count': 1,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # global user completes that playlist
        PlaylistCompletion.objects.create(
            user=GlobalTestCredentials.user,
            playlist=playlist_2)
        response = self.client.get(url)
        expectations = {
            'experience_count': 0,
            'active_experience_count': 0,
            'completed_playlist_count': 1,
            'saved_for_later_count': 1,
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # Delete the playlist created at the start of this test class
        Test.playlist.delete()
        response = self.client.get(url)
        expectations = {
            'experience_count': 0,
            'active_experience_count': 0,
            'completed_playlist_count': 1,
            'saved_for_later_count': 1,
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # delete the playlist that was created in this test
        playlist_2.delete()
        response = self.client.get(url)
        expectations = {
            'experience_count': 0,
            'active_experience_count': 0,
            'completed_playlist_count': 0,
            'saved_for_later_count': 0,
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

    def color_yellow(self, text: str):
        color = colorama.Fore.LIGHTYELLOW_EX
        reset = colorama.Style.RESET_ALL
        return f'{color}{text}{reset}'
