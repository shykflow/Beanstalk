import colorama
import datetime
import warnings

import pytz
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.authtoken.models import Token

from api.models import (
    Playlist,
    PlaylistAccept,
    PlaylistCompletion,
    Experience,
    ExperienceAccept,
    ExperienceCompletion,
    ExperienceSave,
    Post,
    User,
    UserBlock,
    UserFollow,
)
from . import disable_logging, SilenceableAPITestCase


class Test(SilenceableAPITestCase):
    user: User
    user_2: User
    user_3: User
    playlist_by_user: Playlist
    playlist_by_user_2: Playlist
    playlist_by_user_3: Playlist
    experience_by_user: Experience
    experience_by_user_2: Experience
    experience_by_user_3: Experience
    token: Token

    def setUpTestData():
        Test.now = timezone.datetime.now(tz=pytz.timezone("UTC"))
        Test.user = User.objects.create(
            username = 'user',
            email = 'user@email.com',
            email_verified = True,
        )
        Test.user_2 = User.objects.create(
            username = 'user2',
            email = 'user2@email.com',
            email_verified = True,
        )
        Test.user_3 = User.objects.create(
            username = 'user3',
            email = 'user3@email.com',
            email_verified = True,
        )
        Test.playlist_by_user = Playlist.objects.create(
            name = 'test_playlist',
            created_by = Test.user,
        )
        Test.playlist_by_user_2 = Playlist.objects.create(
            name = 'test_playlist',
            created_by = Test.user_2,
        )
        Test.playlist_by_user_3 = Playlist.objects.create(
            name = 'test_playlist',
            created_by = Test.user_3,
        )
        Test.experience_by_user = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.user,
        )
        Test.experience_by_user_2 = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.user_2,
        )
        Test.experience_by_user_3 = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.user_3,
        )

        # When other users accept and complete items it can throw off count
        # If the queries are written incorrectly
        Test.user_2.accepted_experiences.add(Test.experience_by_user)
        Test.user_2.accepted_experiences.add(Test.experience_by_user_2)
        Test.user_2.accepted_experiences.add(Test.experience_by_user_3)
        Test.user_2.accepted_playlists.add(Test.playlist_by_user)
        Test.user_2.accepted_playlists.add(Test.playlist_by_user_2)
        Test.user_2.accepted_playlists.add(Test.playlist_by_user_3)
        Test.user_2.completed_experiences.add(Test.experience_by_user)
        Test.user_2.completed_experiences.add(Test.experience_by_user_2)
        Test.user_2.completed_experiences.add(Test.experience_by_user_3)
        Test.user_2.completed_playlists.add(Test.playlist_by_user)
        Test.user_2.completed_playlists.add(Test.playlist_by_user_2)
        Test.user_2.completed_playlists.add(Test.playlist_by_user_3)

        Test.user_3.accepted_experiences.add(Test.experience_by_user)
        Test.user_3.accepted_experiences.add(Test.experience_by_user_2)
        Test.user_3.accepted_experiences.add(Test.experience_by_user_3)
        Test.user_3.accepted_playlists.add(Test.playlist_by_user)
        Test.user_3.accepted_playlists.add(Test.playlist_by_user_2)
        Test.user_3.accepted_playlists.add(Test.playlist_by_user_3)
        Test.user_3.completed_experiences.add(Test.experience_by_user)
        Test.user_3.completed_experiences.add(Test.experience_by_user_2)
        Test.user_3.completed_experiences.add(Test.experience_by_user_3)
        Test.user_3.completed_playlists.add(Test.playlist_by_user)
        Test.user_3.completed_playlists.add(Test.playlist_by_user_2)
        Test.user_3.completed_playlists.add(Test.playlist_by_user_3)

        Test.token = Token.objects.create(user=Test.user)


    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')


    def test_action_content_counts(self):
        response = self.client.get('/action/content_counts/')
        assert response.status_code == 200
        assert response.data['experience_count'] == 0
        assert response.data['active_experience_count'] == 0
        assert response.data['created_experience_count'] == 1
        assert response.data['completed_playlist_count'] == 0
        assert response.data['saved_for_later_count'] == 0


        # save experience and playlist
        Test.user.saved_experiences.add(Test.experience_by_user_2)
        Test.user.saved_playlists.add(Test.playlist_by_user_2)
        response = self.client.get('/action/content_counts/')
        assert response.status_code == 200
        assert response.data['saved_for_later_count'] == 2

        # active experiences
        Test.user.accepted_experiences.add(Test.experience_by_user_2)
        Test.user.accepted_experiences.add(Test.experience_by_user_3)
        response = self.client.get('/action/content_counts/')
        assert response.status_code == 200
        assert response.data['experience_count'] == 2
        assert response.data['created_experience_count'] == 1
        assert response.data['active_experience_count'] == 2

        # create an experience
        Experience.objects.create(
            name = 'do a thing',
            created_by = Test.user,
        )
        response = self.client.get('/action/content_counts/')
        assert response.status_code == 200
        assert response.data['experience_count'] == 2
        assert response.data['created_experience_count'] == 2
        assert response.data['active_experience_count'] == 2

        # complete experiences and bucketLists
        Test.user.accepted_playlists.add(Test.playlist_by_user_2)
        Test.user.accepted_playlists.add(Test.playlist_by_user_3)
        ExperienceCompletion.objects.create(
            created_at=Test.now,
            user=Test.user,
            experience=Test.experience_by_user_2,
        )
        PlaylistCompletion.objects.create(
            created_at=Test.now,
            user=Test.user,
            playlist=Test.playlist_by_user_2,
        )
        response = self.client.get('/action/content_counts/')
        assert response.status_code == 200
        assert response.data['experience_count'] == 2
        assert response.data['active_experience_count'] == 1
        assert response.data['completed_playlist_count'] == 1

        # block filtering
        Test.blocking_user_block_1: UserBlock = UserBlock.objects.create(
            user = Test.user,
            blocked_user = Test.user_2,
            created_at = Test.now,
        )
        response = self.client.get('/action/content_counts/')
        assert response.status_code == 200
        assert response.data['experience_count'] == 1
        assert response.data['active_experience_count'] == 1
        assert response.data['completed_playlist_count'] == 0
        assert response.data['saved_for_later_count'] == 0


    @disable_logging
    @freeze_time("2022-01-20 00:00:00")
    def test_time_restricted_content(self):
        with warnings.catch_warnings():
            # freeze_time causes harmless timezone awareness warning
            warnings.simplefilter("ignore")
            now = datetime.datetime.now()
            Test.experience_by_user.end_time = now + datetime.timedelta(days=1)
            Test.experience_by_user.save()
            Test.experience_by_user_2.end_time = now + datetime.timedelta(days=30)
            Test.experience_by_user_2.save()
            Test.experience_by_user_3.end_time = now - datetime.timedelta(days=1)
            Test.experience_by_user_3.save()
            Test.playlist_by_user.end_time = now + datetime.timedelta(days=1)
            Test.playlist_by_user.save()
            Test.playlist_by_user_2.end_time = now + datetime.timedelta(days=30)
            Test.playlist_by_user_2.save()
            Test.playlist_by_user_3.end_time = now - datetime.timedelta(days=1)
            Test.playlist_by_user_3.save()
            Test.user.accepted_experiences.add(Test.experience_by_user)
            Test.user.accepted_experiences.add(Test.experience_by_user_2)
            Test.user.accepted_experiences.add(Test.experience_by_user_3)
            Test.user.accepted_playlists.add(Test.playlist_by_user)
            Test.user.accepted_playlists.add(Test.playlist_by_user_2)
            Test.user.accepted_playlists.add(Test.playlist_by_user_3)

            # Get content from this month
            response = self.client.get('/action/time_restricted_content/?start=2022-01-01&end=2022-02-01&minutes_offset=0')
            assert response.status_code == 200
            assert len(response.data) == 2
            contains_experience = False
            contains_playlist = False
            for content in response.data:
                if content['model'] == 'Experience' and content['id'] == Test.experience_by_user.id:
                    contains_experience = True
                elif content['model'] == 'Playlist' and content['id'] == Test.playlist_by_user.id:
                    contains_playlist = True
            assert contains_experience
            assert contains_playlist

            # Get content from next month
            response = self.client.get('/action/time_restricted_content/?start=2022-02-01&end=2022-03-01&minutes_offset=0')
            assert response.status_code == 200
            contains_experience = False
            contains_playlist = False
            for content in response.data:
                if content['model'] == 'Experience' and content['id'] == Test.experience_by_user_2.id:
                    contains_experience = True
                elif content['model'] == 'Playlist' and content['id'] == Test.playlist_by_user_2.id:
                    contains_playlist = True
            assert contains_experience
            assert contains_playlist

            # Don't allow timespan longer than a month
            response = self.client.get('/action/time_restricted_content/?start=2022-02-01&end=2022-03-10&minutes_offset=0')
            assert response.status_code == 400

            # Don't get content from the past
            response = self.client.get('/action/time_restricted_content/?start=2022-01-01&end=2022-01-20&minutes_offset=0')
            assert response.status_code == 200
            assert len(response.data) == 0

            # Respect local time differences
            Test.experience_by_user.use_local_time = True
            Test.experience_by_user.save()
            Test.playlist_by_user.use_local_time = True
            Test.playlist_by_user.save()
            response = self.client.get('/action/time_restricted_content/?start=2022-01-01&end=2022-01-21&minutes_offset=-60')
            assert response.status_code == 200
            assert len(response.data) == 0
            response = self.client.get('/action/time_restricted_content/?start=2022-01-01&end=2022-01-21&minutes_offset=60')
            assert response.status_code == 200
            assert len(response.data) == 2

            # Invalid requests
            with self.assertRaises(ValueError):
                self.client.get('/action/time_restricted_content/?start=abc123&end=2022-01-21&minutes_offset=60')
            with self.assertRaises(ValueError):
                self.client.get('/action/time_restricted_content/?start=2022-01-01&end=abc123&minutes_offset=60')
            with self.assertRaises(ValueError):
                self.client.get('/action/time_restricted_content/?start=2022-01-01&end=2022-01-21&minutes_offset=abc123')
            with self.assertRaises(ValueError):
                self.client.get('/action/time_restricted_content/?start=22-01-01&end=22-01-21&minutes_offset=0')
            with self.assertRaises(ValueError):
                self.client.get('/action/time_restricted_content/?start=01-01-2022&end=01-21-2022&minutes_offset=0')


    def test_saved_content(self):
        response = self.client.get('/action/saved_content/')
        assert response.data['count'] == 0

        Test.user.saved_experiences.add(Test.experience_by_user)
        response = self.client.get('/action/saved_content/')
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == Test.experience_by_user.id

        # The response should be in order of the time the content was saved
        Test.user.saved_experiences.add(Test.experience_by_user_2)
        response = self.client.get('/action/saved_content/')
        assert response.data['count'] == 2
        assert response.data['results'][0]['id'] == Test.experience_by_user.id
        assert response.data['results'][1]['id'] == Test.experience_by_user_2.id

        # It should return both playlists and experiences
        Test.user.saved_playlists.add(Test.playlist_by_user)
        response = self.client.get('/action/saved_content/')
        assert response.data['count'] == 3
        assert response.data['results'][0]['id'] == Test.experience_by_user.id
        assert response.data['results'][1]['id'] == Test.experience_by_user_2.id
        assert response.data['results'][2]['id'] == Test.playlist_by_user.id

        # Remove saved item
        Test.user.saved_experiences.remove(Test.experience_by_user)
        response = self.client.get('/action/saved_content/')
        assert response.data['count'] == 2
        assert response.data['results'][0]['id'] == Test.experience_by_user_2.id
        assert response.data['results'][1]['id'] == Test.playlist_by_user.id


    def test_expect_initial_action_data(self):
        # Test what was created at the start of this test class
        url = f'/action/content_counts/'
        response = self.client.get(url)
        expectations = {
            # Accepted Count
            'experience_count': 0,
            # Accepted and not completed count
            'active_experience_count': 0,
            # Completed Count
            'completed_playlist_count': 0,
            # Completed Count
            'post_count': 0,
            # roughly:
            # user.saved_experiences.count() + user.saved_playlists.count()
            'saved_for_later_count': 0,
            # Any Exp that has an ending time that's within a week
            'upcoming_experience_count': 0,
            # Any Playlist that has an ending time that's within a week
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))


    def test_action_page_expected_chunks(self):
        url = f'/action/content_counts/'
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        # The user follows user_2 and user_2 creates an experience
        UserFollow.objects.create(
            user=Test.user,
            followed_user=Test.user_2)
        experience_from_followed: Experience = Experience.objects.create(
            name='Exp created by followed user',
            created_by=Test.user_2)
        response = self.client.get(url)
        expectations = {
            'experience_count': 0,
            'active_experience_count': 0,
            'completed_playlist_count': 0,
            'post_count': 0,
            'saved_for_later_count': 0,
            'upcoming_experience_count': 0,
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # Accept and save an experience
        experience: Experience = Experience.objects.create(
            name='Owned experience',
            created_by=Test.user_2)
        ExperienceAccept.objects.create(
            user=Test.user,
            experience=experience)
        ExperienceSave.objects.create(
            user=Test.user,
            experience=experience)
        response = self.client.get(url)
        expectations = {
            'experience_count': 1,
            'active_experience_count': 1,
            'completed_playlist_count': 0,
            'post_count': 0,
            'saved_for_later_count': 1,
            'upcoming_experience_count': 0,
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # Accept and save an experience from someone the user follows
        ExperienceAccept.objects.create(
            user=Test.user,
            experience=experience_from_followed)
        ExperienceSave.objects.create(
            user=Test.user,
            experience=experience_from_followed)
        response = self.client.get(url)
        expectations = {
            'experience_count': 2,
            'active_experience_count': 2,
            'completed_playlist_count': 0,
            'post_count': 0,
            'saved_for_later_count': 2,
            'upcoming_experience_count': 0,
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # Accept another experience
        another_experience: Experience = Experience.objects.create(
            created_by=Test.user_2,
            name='Another owned experience',
            end_time=now + datetime.timedelta(hours=6))
        ExperienceAccept.objects.create(
            user=Test.user,
            experience=another_experience)
        response = self.client.get(url)
        expectations = {
            'experience_count': 3,
            'active_experience_count': 3,
            'completed_playlist_count': 0,
            'post_count': 0,
            'saved_for_later_count': 2,
            'upcoming_experience_count': 1,
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # Accept a playlist
        playlist: Playlist = Playlist.objects.create(
            created_by=Test.user_2,
            name="User created",
            end_time=now + datetime.timedelta(hours=6))
        PlaylistAccept.objects.create(
            user=Test.user,
            playlist=playlist)
        response = self.client.get(url)
        expectations = {
            'experience_count': 3,
            'active_experience_count': 3,
            'completed_playlist_count': 0,
            'post_count': 0,
            'saved_for_later_count': 2,
            'upcoming_experience_count': 1,
            'upcoming_playlist_count': 1,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # Complete that playlist
        PlaylistCompletion.objects.create(
            user=Test.user,
            playlist=playlist)
        response = self.client.get(url)
        expectations = {
            'experience_count': 3,
            'active_experience_count': 3,
            'completed_playlist_count': 1,
            'post_count': 0,
            'saved_for_later_count': 2,
            'upcoming_experience_count': 1,
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # Create a Post
        Post.objects.create(
            created_by=Test.user,
            name='post')
        response = self.client.get(url)
        expectations = {
            'experience_count': 3,
            'active_experience_count': 3,
            'completed_playlist_count': 1,
            'post_count': 1,
            'saved_for_later_count': 2,
            'upcoming_experience_count': 1,
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))


    def test_completed_content(self):
        uri = f'/users/{Test.user.id}/completed_content/'
        response = self.client.get(uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        Test.user.completed_experiences.add(Test.experience_by_user)
        response = self.client.get(uri)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], Test.experience_by_user.id)

        # The response should be in reverse order of when the content was completed
        Test.user.completed_experiences.add(Test.experience_by_user_2)
        response = self.client.get(uri)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['id'], Test.experience_by_user_2.id)
        self.assertEqual(response.data['results'][1]['id'], Test.experience_by_user.id)

        # It should return both playlists and experiences
        Test.user.completed_playlists.add(Test.playlist_by_user)
        response = self.client.get(uri)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['results'][0]['id'], Test.playlist_by_user.id)
        self.assertEqual(response.data['results'][1]['id'], Test.experience_by_user_2.id)
        self.assertEqual(response.data['results'][2]['id'], Test.experience_by_user.id)

        # Remove completed content
        Test.user.completed_experiences.remove(Test.experience_by_user)
        response = self.client.get(uri)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['id'], Test.playlist_by_user.id)
        self.assertEqual(response.data['results'][1]['id'], Test.experience_by_user_2.id)


    def color_yellow(self, text: str):
        color = colorama.Fore.LIGHTYELLOW_EX
        reset = colorama.Style.RESET_ALL
        return f'{color}{text}{reset}'
