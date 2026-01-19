import datetime
import json

from django.utils import timezone
from freezegun import freeze_time
from rest_framework.authtoken.models import Token
from api.enums import ActivityType, Publicity

from api.models import (
    Activity,
    Playlist,
    Experience,
    User,
    PlaylistAccept,
    PlaylistSave,
    PlaylistCompletion,
    ExperienceAccept,
    ExperienceCompletion,
    Post
)
from api.testing_overrides import TestFiles
from . import disable_logging, SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    user_one: User
    user_two: User
    user_other: User
    playlist: Playlist
    experience_one: Experience
    experience_two: Experience
    token_one: Token
    token_two: Token
    auth_header_user_one: dict[str, str]
    auth_header_user_two: dict[str, str]

    def setUpTestData():
        Test.user_one = User.objects.create(
            username = 'test_user_one',
            email = 'testuserone@email.com',
            email_verified = True)
        Test.user_two = User.objects.create(
            username = 'test_user_two',
            email = 'testusertwo@email.com',
            email_verified = True)
        Test.user_other = User.objects.create(
            username = 'test_user_other',
            email = 'testuserother@email.com',
            email_verified = True)
        Test.playlist = Playlist.objects.create(
            name = 'test_playlist',
            created_by = Test.user_one)
        Test.experience_one = Experience.objects.create(
            created_by = Test.user_other,
            name = 'test_experience_one')
        Test.experience_two = Experience.objects.create(
            created_by = Test.user_other,
            name = 'test_experience_two')
        Test.token_one = Token.objects.create(user=Test.user_one)
        Test.token_two = Token.objects.create(user=Test.user_two)
        Test.auth_header_user_one = {'HTTP_AUTHORIZATION': f'Bearer {Test.token_one}'}
        Test.auth_header_user_two = {'HTTP_AUTHORIZATION': f'Bearer {Test.token_two}'}

    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_one}')

    def test_retrieve_model(self):
        # GET valid playlist
        response = self.client.get(f'/playlists/{Test.playlist.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'test_playlist')
        self.assertEqual(response.data['created_by']['id'], Test.user_one.id)
        self.assertEqual(response.data['created_by']['username'], Test.user_one.username)
        self.assertEqual(response.data['num_experiences'], 0)
        self.assertEqual(response.data['num_completed_experiences'], 0)

        # GET invalid playlist
        response = self.client.get('/playlists/-1/')
        self.assertEqual(response.status_code, 404)


    def test_create_model(self):
        # POST valid
        response = self.client.post('/playlists/', {
            'json': json.dumps({
                'name': 'test_playlist_two',
            })
        })
        self.assertEqual(response.status_code, 201)

        # POST invalid playlist (no name)
        response = self.client.post('/playlists/', {
        }, format='json')
        self.assertEqual(response.status_code, 400)


    def test_create_accepts_playlist(self):
        response = self.client.post('/playlists/', {
            'json': json.dumps({
                'name': 'test_playlist_two',
                'experiences': [Test.experience_one.id, Test.experience_two.id],
            })
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['user_accepted'])
        self.assertTrue(PlaylistAccept.objects \
            .filter(user=Test.user_one, playlist__id=response.data['id']).exists())

    def test_update_model(self):
        # PUT valid playlist name
        response = self.client.put(f'/playlists/{Test.playlist.id}/', {
            'json': json.dumps({
                'name': 'test_playlist_updated',
                'replace_highlight_image': False,
                'replace_video': False,
            })
        })
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['name'], 'test_playlist_updated')

        # PUT invalid playlist no name included
        response = self.client.put(f'/playlists/{Test.playlist.id}/', {
            'json': json.dumps({
                'experiences': [Test.experience_one.id]
            })
        })
        self.assertEqual(response.status_code, 400)

        # PUT valid playlist as strings, not json
        # This is because the phone sends put requests with form data (all strings)
        # not json when uploading images.
        response = self.client.put(f'/playlists/{Test.playlist.id}/', {
            'json': json.dumps({
                'name': 'test_playlist_updated',
                'editability': str(Publicity.PUBLIC.value),
                'visibility': str(Publicity.PUBLIC.value),
                'start_time_date_only': 'true',
                'end_time_date_only': 'true',
                'use_local_time': 'true',
                'file_is_image': 'true',
                'replace_highlight_image': False,
                'replace_video': False,
            })
        })
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['name'], 'test_playlist_updated')

        # PUT valid playlist remove experiences
        response = self.client.put(f'/playlists/{Test.playlist.id}/', {
            'json': json.dumps({
                'name': 'test_playlist_updated',
                'replace_highlight_image': False,
                'replace_video': False,
                'experiences': [],
            })
        })
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['num_experiences'], 0)
        playlist_id = response.data['id']
        response = self.client.get(f'/playlists/{playlist_id}/experiences/')
        experience_ids = [x['id'] for x in response.data['results']]
        self.assertNotIn(Test.experience_one.id, experience_ids)
        self.assertNotIn(Test.experience_two.id, experience_ids)

        # PUT valid playlist make private
        response = self.client.put(f'/playlists/{Test.playlist.id}/', {
            'json': json.dumps({
                'name': 'test_playlist_updated',
                'replace_highlight_image': False,
                'replace_video': False,
                'visibility': 3
            })
        })
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['visibility'], 3)

        # PUT make sure it doesn't fail with attachments even though they are ignored
        response = self.client.put(f'/playlists/{Test.playlist.id}/', {
            'json': json.dumps({
                'name': 'test_playlist_updated',
                'replace_highlight_image': False,
                'replace_video': False,
                'attachments': []
            })
        })
        self.assertEqual(response.status_code, 202)

        # PUT different user attempted to change playlist
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.put(f'/playlists/{Test.playlist.id}/', {
            'json': json.dumps({
                'name': 'test_playlist_updated',
                'replace_highlight_image': False,
                'replace_video': False,
            })
        })
        self.assertEqual(response.status_code, 401)


    def test_list_model(self):
        playlist_qs = Playlist.objects.all()
        self.assertEqual(playlist_qs.count(), 1)
        playlist = playlist_qs.first()
        self.assertEqual(playlist.name, 'test_playlist')
        self.assertEqual(playlist.created_by.id, Test.user_one.id)
        self.assertEqual(playlist.created_by.username, Test.user_one.username)

        # POST valid playlist for user two
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.post('/playlists/', {
            'json': json.dumps({
                'name': 'test_playlist_two',
            })
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'test_playlist_two')
        self.assertEqual(response.data['num_experiences'], 0)
        self.assertEqual(response.data['created_by']['id'], Test.user_two.id)
        playlist_id = response.data['id']
        response = self.client.get(f'/playlists/{playlist_id}/experiences/')
        self.assertEqual(response.data['count'], 0)

        # GET playlists filtered by created_by user_one
        response = self.client.get(f'/playlists/?created_by={Test.user_one.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        playlist = response.data['results'][0]
        self.assertEqual(playlist['name'] , 'test_playlist')
        self.assertEqual(playlist['created_by']['id'], Test.user_one.id)

        # GET playlists filtered by created_by user_two
        response = self.client.get(f'/playlists/?created_by={Test.user_two.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        playlist = response.data['results'][0]
        self.assertEqual(playlist['name'] , 'test_playlist_two')
        self.assertEqual(playlist['created_by']['id'], Test.user_two.id)

        response = self.client.get(f'/users/-1/playlists/')
        self.assertEqual(response.status_code, 404)

        # Poorly written queries will show duplicates when other users have accepted/completed experiences
        user_three = User.objects.create(
            username = 'test_user_three',
            email = 'testuserthree@email.com',
            email_verified = True)
        user_three.accepted_experiences.add(Test.experience_one)
        user_three.accepted_playlists.add(Test.playlist)
        user_three.completed_playlists.add(Test.playlist)
        Test.experience_one.calc_total_accepts(set_and_save=True)
        Test.playlist.calc_total_accepts(set_and_save=True)
        Test.playlist.calc_total_completes(set_and_save=True)

        # Filter with accepted
        Test.user_two : User
        Test.user_two.accepted_playlists.add(Test.playlist)
        Test.playlist.calc_total_accepts(set_and_save=True)
        response = self.client.get(f'/users/{Test.user_two.id}/accepted_playlists/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        playlist = response.data['results'][0]
        self.assertEqual(playlist['num_experiences'], 0)
        self.assertEqual(playlist['num_completed_experiences'], 0)
        Test.user_two.accepted_playlists.remove(Test.playlist)
        response = self.client.get(f'/users/{Test.user_two.id}/accepted_playlists/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)


    def test_list_model_experience_counts(self):
        # Add 10 experiences and complete 5
        for i in range(10):
            exp: Experience = Experience.objects.create(
                created_by=Test.user_other,
                name='test_experience_one')
            Test.playlist.experiences.add(exp)
            if i % 2 == 0:
                Test.user_one.completed_experiences.add(exp)
                exp.calc_total_completes(set_and_save=True)

        response = self.client.get(f'/playlists/?created_by={Test.user_one.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        playlist = response.data['results'][0]
        self.assertEqual(playlist['num_experiences'], 10)
        self.assertEqual(playlist['num_completed_experiences'], 5)
        self.assertEqual(playlist['name'] , 'test_playlist')
        self.assertEqual(playlist['created_by']['id'], Test.user_one.id)


    def test_list_model_include_experiences_ids(self):
        Playlist.objects.create(
            name = 'test_playlist_two',
            created_by = Test.user_one)
        Test.playlist.experiences.add(Test.experience_one)
        response = self.client.get(f'/playlists/?created_by={Test.user_one.id}&include_experience_ids=true')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.experience_one.id, response.data['results'][0]['experience_ids'])
        self.assertIn(self.experience_one.id, response.data['results'][1]['experience_ids'])


    @disable_logging
    def test_invalid_list_model(self):
        with self.assertRaises(ValueError):
            self.client.get('/playlists/?created_by=abc123')
        with self.assertRaises(ValueError):
            self.client.get('/playlists/?created_by=1.1')


    def test_destroy_model(self):
        # DELETE playlist user_one created
        response = self.client.delete(f'/playlists/{Test.playlist.id}/',)
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(response.data)

        # GET should 404 now
        response = self.client.get(f'/playlists/{Test.playlist.id}/')
        self.assertEqual(response.status_code, 404)

        # DELETE on the same playlist should 404
        response = self.client.delete(f'/playlists/{Test.playlist.id}/',)
        self.assertEqual(response.status_code, 404)

        # Create a playlist created by user_two
        other_playlist: Playlist = Playlist.objects.create(
            name = 'other_test_playlist',
            created_by = Test.user_two,
        )

        # DELETE on playlist that is not your own should 401
        response = self.client.delete(f'/playlists/{other_playlist.id}/',)
        self.assertEqual(response.status_code, 401)


    def test_mark_seen(self):
        with self.settings(SKIP_MARK_FOLLOW_FEED_SEEN=False):
            self.assertEqual(Test.user_one.seen_playlists.all().count(), 0)

            response = self.client.post(f'/playlists/{Test.playlist.id}/mark_seen/')
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.data)

            self.assertEqual(Test.user_one.seen_playlists.all().count(), 1)


    def test_playlist_experiences(self):
        endpoint = f'/playlists/{Test.playlist.id}/experiences/'
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        experiences = {'experiences': [Test.experience_one.id, Test.experience_two.id]}
        response = self.client.post(endpoint, data=experiences, format='json')
        self.assertEqual(response.status_code, 200)

        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

        # Bad requests should 400
        response = self.client.post(endpoint)
        self.assertEqual(response.status_code, 400)
        response = self.client.post(endpoint, data={'abc': [1, 2, 3]}, format='json')
        self.assertEqual(response.status_code, 400)
        response = self.client.post(endpoint, data={'experiences': 1}, format='json')
        self.assertEqual(response.status_code, 400)

        response = self.client.delete(endpoint, data=experiences, format='json')
        self.assertEqual(response.status_code, 200)

        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        # Bad requests should 400
        response = self.client.delete(endpoint)
        self.assertEqual(response.status_code, 400)
        response = self.client.delete(endpoint, data={'abc': [1, 2, 3]}, format='json')
        self.assertEqual(response.status_code, 400)
        response = self.client.delete(endpoint, data={'experiences': 1}, format='json')
        self.assertEqual(response.status_code, 400)


    def test_accept_playlist(self):
        response = self.client.post(f'/playlists/{Test.playlist.id}/accept/')
        assert response.status_code == 200
        accept = PlaylistAccept.objects.filter(playlist=Test.playlist.id).first()
        assert accept.user.id == Test.user_one.id

        response = self.client.delete(f'/playlists/{Test.playlist.id}/accept/')
        assert response.status_code == 204
        accept = PlaylistAccept.objects.filter(playlist=Test.playlist.id).first()
        assert accept == None

        # Don't accept all experiences within a playlist
        user: User = Test.user_one
        Test.playlist.experiences.add(Test.experience_one.id)
        Test.playlist.experiences.add(Test.experience_two.id)
        response = self.client.post(f'/playlists/{Test.playlist.id}/accept/?accept_experiences=false')
        assert not user.accepted_experiences.filter(id=Test.experience_one.id).exists()
        assert not user.accepted_experiences.filter(id=Test.experience_two.id).exists()

        # Accept all experiences within a playlist
        response = self.client.post(f'/playlists/{Test.playlist.id}/accept/?accept_experiences=true')
        assert user.accepted_experiences.filter(id=Test.experience_one.id).exists()
        assert user.accepted_experiences.filter(id=Test.experience_two.id).exists()
        self.assertEqual(response.data['num_accepted_experiences'], 2)
        self.assertEqual(ExperienceAccept.objects.count(), 2)

        # Repeating the request doesn't create multiple ExperienceAccept records
        response = self.client.post(f'/playlists/{Test.playlist.id}/accept/?accept_experiences=true')
        self.assertEqual(response.data['num_accepted_experiences'], 0)
        self.assertEqual(ExperienceAccept.objects.count(), 2)



    def test_save_playlist(self):
        response = self.client.post(f'/playlists/{Test.playlist.id}/save/')
        assert response.status_code == 200
        accept = PlaylistSave.objects.filter(playlist=Test.playlist.id).first()
        assert accept.user.id == Test.user_one.id

        response = self.client.delete(f'/playlists/{Test.playlist.id}/save/')
        assert response.status_code == 204
        accept = PlaylistSave.objects.filter(playlist=Test.playlist.id).first()
        assert accept == None


    def test_playlist_pin(self):
        playlist_two = Playlist.objects.create(
            name = 'test_playlist_2',
            created_by = Test.user_one,
        )
        playlist_three = Playlist.objects.create(
            name = 'test_playlist_3',
            created_by = Test.user_one,
        )

        response = self.client.post(f'/playlists/{Test.playlist.id}/pin/')
        assert response.status_code == 200
        response = self.client.get(f'/users/{Test.user_one.id}/pinned_playlists/')
        assert response.status_code == 200
        assert response.data['results'][0]['id'] == Test.playlist.id

        response = self.client.delete(f'/playlists/{Test.playlist.id}/pin/')
        assert response.status_code == 204
        response = self.client.get(f'/users/{Test.user_one.id}/pinned_playlists/')
        assert response.status_code == 200
        assert response.data['count'] == 0

        pin_list = [Test.playlist.id, playlist_two.id, playlist_three.id]
        response = self.client.put(f'/users/{Test.playlist.id}/pinned_playlists/', data=pin_list, format='json')
        assert response.status_code == 200
        response = self.client.get(f'/users/{Test.user_one.id}/pinned_playlists/')
        assert response.status_code == 200
        assert response.data['results'][0]['id'] == Test.playlist.id
        assert response.data['results'][1]['id'] == playlist_two.id
        assert response.data['results'][2]['id'] == playlist_three.id

        self.client.delete(f'/playlists/{playlist_two.id}/pin/')
        response = self.client.get(f'/users/{Test.user_one.id}/pinned_playlists/')
        assert response.status_code == 200
        assert response.data['count'] == 2
        assert response.data['results'][0]['id'] == Test.playlist.id
        assert response.data['results'][1]['id'] == playlist_three.id

        pin_list = [playlist_two.id]
        response = self.client.put(f'/users/{Test.playlist.id}/pinned_playlists/', data=pin_list, format='json')
        response = self.client.get(f'/users/{Test.user_one.id}/pinned_playlists/')
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == playlist_two.id


    def test_complete_playlist(self):
        # Don't complete the playlist if there are no experiences
        PlaylistAccept.objects.create(
            playlist = Test.playlist,
            user = Test.user_one,)

        response = self.client.post(f'/playlists/{Test.playlist.id}/complete/', data={'minutes_offset': 0})
        assert response.status_code == 400
        assert not PlaylistCompletion.objects.filter(playlist=Test.playlist.id).exists()

        # Don't complete the playlist if its experiences are not complete
        Test.playlist.experiences.add(Test.experience_one)
        Test.playlist.experiences.add(Test.experience_two)
        response = self.client.post(f'/playlists/{Test.playlist.id}/complete/', data={'minutes_offset': 0})
        assert response.status_code == 400
        assert not PlaylistCompletion.objects.filter(playlist=Test.playlist.id).exists()

        # Complete playlist
        ExperienceCompletion.objects.create(
            experience=Test.experience_one,
            user=Test.user_one)
        ExperienceCompletion.objects.create(
            experience=Test.experience_two,
            user=Test.user_one)
        response = self.client.post(f'/playlists/{Test.playlist.id}/complete/', data={'minutes_offset': 0})
        assert response.status_code == 200
        assert PlaylistCompletion.objects.filter(playlist=Test.playlist.id).exists()

        # Don't complete playlists twice
        response = self.client.post(f'/playlists/{Test.playlist.id}/complete/', data={'minutes_offset': 0})
        assert response.status_code == 400

        # Create post on playlist completion
        playlist_two: Playlist = Playlist.objects.create(
            name = 'test_playlist',
            created_by = Test.user_one,
        )
        playlist_two.experiences.add(Test.experience_one)
        text = 'test_completion_post_text'
        PlaylistAccept.objects.create(
            playlist = playlist_two,
            user = Test.user_one,)
        data = {
            'post': {
                'text': text,
                'name': 'name',
            },
            'minutes_offset': 0,
        }
        response = self.client.post(f'/playlists/{playlist_two.id}/complete/', data=data,format='json')
        assert response.status_code == 201
        assert Post.objects.filter(text=text).exists()
        assert PlaylistCompletion.objects.filter(playlist=playlist_two.id).exists()


    @freeze_time("2022-01-20 10:00:00")
    def test_playlist_complete_time(self):
        playlist : Playlist = Test.playlist

        self.client.post(f'/playlists/{Test.playlist.id}/accept/')
        PlaylistAccept.objects.create(
            playlist = playlist,
            user = Test.user_one,)
        now = datetime.datetime.now(tz=timezone.utc)
        playlist.experiences.add(Test.experience_one)
        ExperienceCompletion.objects.create(
            experience = Test.experience_one,
            user = Test.user_one,)

        # Don't accept 1 day before start with start_time_date_only
        playlist.start_time = now + datetime.timedelta(days=1)
        playlist.start_time_date_only = True
        playlist.save()
        response = self.client.post(f'/playlists/{playlist.id}/complete/', data={'minutes_offset': 0})
        assert response.status_code == 400

        # Don't accept 1 minute before start without start_time_date_only
        playlist.start_time_date_only = False
        playlist.start_time = now + datetime.timedelta(minutes=1)
        playlist.save()
        response = self.client.post(f'/playlists/{playlist.id}/complete/', data={'minutes_offset': 0})
        assert response.status_code == 400

        # Don't accept 1 day after start with end_time_date_only
        playlist.start_time = None
        playlist.end_time = now - datetime.timedelta(days=1)
        playlist.end_time_date_only = True
        playlist.save()
        response = self.client.post(f'/playlists/{playlist.id}/complete/', data={'minutes_offset': 0})
        assert response.status_code == 400

        # Don't accept 1 minute after start without end_time_date_only
        playlist.end_time = now - datetime.timedelta(minutes=1)
        playlist.end_time_date_only = False
        playlist.save()
        response = self.client.post(f'/playlists/{playlist.id}/complete/', data={'minutes_offset': 0})
        assert response.status_code == 400

        # Don't allow offset > |24| hours
        playlist.end_time = None
        playlist.save()
        response = self.client.post(f'/playlists/{playlist.id}/complete/', data={'minutes_offset': 1441})
        assert response.status_code == 400
        response = self.client.post(f'/playlists/{playlist.id}/complete/', data={'minutes_offset': -1441})
        assert response.status_code == 400

        # Don't accept if the offset falls 1 minute outside of playlist start
        playlist.start_time = now
        playlist.start_time_date_only = False
        playlist.save()
        response = self.client.post(f'/playlists/{playlist.id}/complete/', data={'minutes_offset': -1})
        assert response.status_code == 400

        # Don't accept if the offset falls 1 minute outside of playlist end
        playlist.start_time = None
        playlist.end_time = now
        playlist.end_time_date_only = False
        playlist.save()
        response = self.client.post(f'/playlists/{playlist.id}/complete/', data={'minutes_offset': 1})
        assert response.status_code == 400

        # Accept playlist within tight bounds
        playlist.start_time = now - datetime.timedelta(minutes=1)
        playlist.end_time = now + datetime.timedelta(minutes=1)
        playlist.start_time_date_only = False
        playlist.end_time_date_only = False
        playlist.save()
        response = self.client.post(f'/playlists/{playlist.id}/complete/', data={'minutes_offset': 0})
        assert response.status_code == 200
        completion = PlaylistCompletion.objects.filter(playlist=playlist.id)
        assert completion.exists()

        # Accept playlist within 1 day bounds with date_only
        # Start day should act inclusively and end day should be exclusively
        completion.delete()
        playlist.start_time = now
        playlist.start_time_date_only = True
        playlist.end_time = now + datetime.timedelta(days=1)
        playlist.end_time_date_only = True
        playlist.save()
        response = self.client.post(f'/playlists/{playlist.id}/complete/', data={'minutes_offset': 0})
        assert response.status_code == 200
        completion = PlaylistCompletion.objects.filter(playlist=playlist.id)
        assert completion.exists()

    def test_playlist_accept_creates_activity(self):
        Test.playlist.experiences.add(Test.experience_one.id)
        Test.user_two.completed_experiences.add(Test.experience_one)
        Test.experience_one.calc_total_completes(set_and_save=True)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        self.client.post(f'/playlists/{Test.playlist.id}/accept/?accept_experiences=true')

        # Should not raise exception since now a matching Activity exists
        generated_activity: Activity = Activity.objects.get(playlist=Test.playlist, type=ActivityType.ACCEPTED_PLAYLIST)
        self.assertEqual(generated_activity.user, Test.user_one)
        self.assertEqual(generated_activity.related_user, Test.user_two)
        self.assertEqual(generated_activity.type, 402)
        self.assertEqual(generated_activity.playlist.id, Test.playlist.id)

    def test_own_playlist_accept_does_not_create_activity(self):
        Test.playlist.experiences.add(Test.experience_one.id)
        Test.user_two.completed_experiences.add(Test.experience_one)
        Test.experience_one.calc_total_completes(set_and_save=True)
        response=self.client.post(f'/playlists/{Test.playlist.id}/accept/?accept_experiences=true')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Activity.objects.filter(
            user=Test.user_one,
            playlist=Test.playlist,
            type=ActivityType.ACCEPTED_PLAYLIST).exists())

    def test_playlist_completion_creates_activity(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        Test.playlist.experiences.add(Test.experience_one.id)
        Test.user_two.completed_experiences.add(Test.experience_one)
        Test.experience_one.calc_total_completes(set_and_save=True)
        self.client.post(f'/playlists/{Test.playlist.id}/accept/?accept_experiences=true')

        self.assertFalse(Activity.objects.filter(
            user=Test.user_one,
            playlist=Test.playlist,
            type=ActivityType.COMPLETED_PLAYLIST,
            related_user=Test.user_two).exists())
        self.client.post(f'/playlists/{Test.playlist.id}/complete/', data={'minutes_offset': 0})
        self.assertTrue(Activity.objects.filter(
            user=Test.user_one,
            playlist=Test.playlist,
            type=ActivityType.COMPLETED_PLAYLIST,
            related_user=Test.user_two).exists())

    def test_own_playlist_completion_does_not_create_activity(self):
        Test.playlist.experiences.add(Test.experience_one.id)
        Test.user_one.completed_experiences.add(Test.experience_one)
        Test.experience_one.calc_total_completes(set_and_save=True)
        self.client.post(f'/playlists/{Test.playlist.id}/accept/?accept_experiences=true')
        response = self.client.post(f'/playlists/{Test.playlist.id}/complete/', data={'minutes_offset': 0})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Activity.objects.filter(
            user=Test.user_one,
            playlist=Test.playlist,
            type=ActivityType.COMPLETED_PLAYLIST).exists())


    @freeze_time("2022-12-20 10:00:00")
    def test_updated_experience_by_setting_nulls(self):
        response = self.client.post('/playlists/', {
            'highlight_image': TestFiles.get_simple_uploaded_file('jpg'),
            'highlight_image_thumbnail': TestFiles.get_simple_uploaded_file('jpg'),
            'video': TestFiles.get_simple_uploaded_file('mp4'),
            'json': json.dumps({
                'name': 'name',
                'description': 'test description',
                'start_time': '2022-11-23T00:00:00.00Z',
                'end_time': '2022-12-23T00:00:00.00Z',
            })
        })
        self.assertEqual(response.status_code, 201)

        # Remove start/end times, description, highlight_image, thumbnail, and video
        id = response.data['id']
        response = self.client.put(f'/playlists/{id}/', data={
            'json': json.dumps({
                'name': 'name',
                'description': None,
                'end_time': None,
                'start_time': None,
                'replace_highlight_image_thumbnail': True,
                'replace_highlight_image': True,
                'replace_video': True,
            })
        })
        self.assertEqual(response.status_code, 202)
        pl: Playlist = Playlist.objects.filter(id=id).first()
        self.assertIsNone(pl.description)
        self.assertIsNone(pl.end_time)
        self.assertIsNone(pl.start_time)

        # images/videos will still be type ImageFieldFile/FieldFile, but their effective value is None
        # They raise a value error if None, since a ImageFieldFile: None has no url
        with self.assertRaises(ValueError):
            pl.highlight_image.url
        with self.assertRaises(ValueError):
            pl.highlight_image_thumbnail.url
        with self.assertRaises(ValueError):
            pl.video.url

    def test_retrieve_accepted_users(self):
        PlaylistAccept.objects.create(
            playlist = Test.playlist,
            user = Test.user_one)
        PlaylistAccept.objects.create(
            playlist = Test.playlist,
            user = Test.user_two)
        response = self.client.get(f'/playlists/{Test.playlist.id}/accepted_users/')
        self.assertEqual(response.status_code, 200)
        # Should be in reverse order of the accept's creation
        self.assertEqual(response.data['results'][0]['model'], 'User')
        self.assertEqual(response.data['results'][0]['id'], Test.user_two.id)
        self.assertEqual(response.data['results'][1]['id'], Test.user_one.id)


    def test_retrieve_playlist_posts(self):
        post_one = Post.objects.create(
            created_by=Test.user_one,
            playlist=Test.playlist,
            name='test post one',
            text='test post one text'
        )
        post_two = Post.objects.create(
            created_by=Test.user_two,
            playlist=Test.playlist,
            name='test post two',
            text='test post two text'
        )

        response = self.client.get(f'/playlists/{Test.playlist.id}/posts/')
        self.assertEqual(response.status_code, 200)
        # Should be in reverse order of the post's creation
        self.assertEqual(response.data['results'][0]['model'], 'Post')
        self.assertEqual(response.data['results'][0]['id'], post_two.id)
        self.assertEqual(response.data['results'][1]['id'], post_one.id)




    def test_playlist_has_correct_total_accepts(self):
        other_user: User = User.objects.create(
            username='other',
            email='other@email.com',
            email_verified=True)
        pl: Playlist = Playlist.objects.create(
            name='asdf',
            created_by=Test.user_one)
        endpoint = f'/playlists/{pl.id}/?details=true'

        response = self.client.get(endpoint)
        pl_dict: dict[str, any] = response.data
        self.assertEqual(pl_dict['total_accepts'], 0)

        Test.user_one.accepted_playlists.add(pl)
        pl.calc_total_accepts(set_and_save=True)
        response = self.client.get(endpoint)
        pl_dict: dict[str, any] = response.data
        self.assertEqual(pl_dict['total_accepts'], 1)

        other_user.accepted_playlists.add(pl)
        pl.calc_total_accepts(set_and_save=True)
        response = self.client.get(endpoint)
        pl_dict: dict[str, any] = response.data
        self.assertEqual(pl_dict['total_accepts'], 2)


    def test_playlist_has_correct_total_completes(self):
        other_user: User = User.objects.create(
            username='other',
            email='other@email.com',
            email_verified=True)
        pl: Playlist = Playlist.objects.create(
            name='asdf',
            created_by=Test.user_one)
        endpoint = f'/playlists/{pl.id}/?details=true'

        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_completes'], 0)

        Test.user_one.completed_playlists.add(pl)
        pl.calc_total_completes(set_and_save=True)
        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_completes'], 1)

        other_user.completed_playlists.add(pl)
        pl.calc_total_completes(set_and_save=True)
        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_completes'], 2)


    def test_playlist_has_correct_total_likes(self):
        other_user: User = User.objects.create(
            username='other',
            email='other@email.com',
            email_verified=True)
        pl: Playlist = Playlist.objects.create(
            name='asdf',
            created_by=Test.user_one)
        endpoint = f'/playlists/{pl.id}/?details=true'

        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_likes'], 0)

        pl.likes.add(Test.user_one)
        pl.calc_total_likes(set_and_save=True)
        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_likes'], 1)

        pl.likes.add(other_user)
        pl.calc_total_likes(set_and_save=True)
        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_likes'], 2)
