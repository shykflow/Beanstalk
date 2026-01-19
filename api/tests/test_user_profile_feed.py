import datetime
from api.models import (
    User,
    Playlist,
    PlaylistAccept,
    PlaylistCompletion,
    Experience,
    ExperienceAccept,
    ExperienceCompletion,
    Post)
from . import SilenceableAPITestCase
from rest_framework.authtoken.models import Token
from api.views.user import PROFILE_FEED_SLICE_SIZE

class Test(SilenceableAPITestCase):
    user_one: User
    user_two: User
    user_three: User
    token: Token

    def setUpTestData():
        Test.user_one = User.objects.create(
            username = 'test_user_one',
            email = 'testuserone@email.com',
            email_verified = True)
        Test.user_two = User.objects.create(
            username = 'test_user_two',
            email = 'testusertwo@email.com',
            email_verified = True)
        Test.user_three = User.objects.create(
            username = 'test_user_three',
            email = 'testuserthree@email.com',
            email_verified = True)
        Test.playlist_one = Playlist.objects.create(
            created_at=datetime.datetime(2022, 12, 5),
            created_by=Test.user_two,
            name='Playlist One')
        Test.playlist_two = Playlist.objects.create(
            created_by=Test.user_three,
            name='Playlist Two')
        Test.experience_one = Experience.objects.create(
            created_at=datetime.datetime(2022, 12, 6),
            created_by=Test.user_two,
            name='Experience One')
        Test.experience_two = Experience.objects.create(
            created_by=Test.user_three,
            name='Experience Two')
        Test.post_one = Post.objects.create(
            created_at=datetime.datetime(2022, 12, 7),
            created_by=Test.user_two,
            experience=Test.experience_one,
            text='Post One',
            name='name')
        Test.post_two = Post.objects.create(
            created_by=Test.user_three,
            playlist=Test.playlist_one,
            text='Post two',
            name='name')

        Test.token = Token.objects.create(
            user=Test.user_one)


    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')


    def test_profiles_feed(self):
        endpoint_url = f'/users/{Test.user_two.id}/profile_feed/' + \
            '?experiences=true' + \
            '&playlists=true' + \
            '&posts=true'
        response = self.client.get(endpoint_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertTrue(response.data['seen_all'])
        # They should be in reverse chronological order
        results = response.data['results']
        self.assertEqual(results[0]['model'], 'Post')
        self.assertEqual(results[0]['id'], Test.post_one.id)
        self.assertEqual(results[1]['model'], 'Experience')
        self.assertEqual(results[1]['id'], Test.experience_one.id)
        self.assertEqual(results[2]['model'], 'Playlist')
        self.assertEqual(results[2]['id'], Test.playlist_one.id)


    def test_profiles_feed_experiences_only(self):
        endpoint_url = f'/users/{Test.user_two.id}/profile_feed/' + \
            '?experiences=true'
        response = self.client.get(endpoint_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['seen_all'])
        results = response.data['results']
        self.assertEqual(results[0]['id'], Test.experience_one.id)


    def test_profiles_feed_playlist_only(self):
        endpoint_url = f'/users/{Test.user_two.id}/profile_feed/' + \
            '?playlists=true'
        response = self.client.get(endpoint_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['seen_all'])
        results = response.data['results']
        self.assertEqual(results[0]['id'], Test.playlist_one.id)


    def test_profiles_feed_continuated_results(self):
        # The profile feed attempts to get the slice size for 7 different
        # types of data.
        max_per_page = PROFILE_FEED_SLICE_SIZE * 7
        # Create a lots of content create by user_one
        playlists = []
        experiences = []
        posts = []

        # Make more than 1 page of data
        while len(playlists) + len(experiences) + len(posts) <= max_per_page:
            exp = Experience(name=f"test_exp", created_by=Test.user_one)
            experiences.append(exp)
            pl = Playlist(name=f"test_playlist", created_by=Test.user_one)
            playlists.append(pl)
            # No pointer post
            posts.append(Post(
                text=f'test_post',
                created_by=Test.user_one))
            # Experience post
            posts.append(Post(
                text=f'test_exp_post',
                created_by=Test.user_one,
                experience=exp))
            # Playlist post
            posts.append(Post(
                text=f'test_pl_post',
                created_by=Test.user_one,
                playlist=pl))
        Experience.objects.bulk_create(experiences)
        Playlist.objects.bulk_create(playlists)
        Post.objects.bulk_create(posts)
        created_count = len(playlists) + len(experiences) + len(posts)

        playlist_ids = [x.id for x in playlists]
        experience_ids = [x.id for x in experiences]
        post_ids = [x.id for x in posts]

        all_results: list[dict[str, any]] = []

        # Get all pages of the continuation
        base_endpoint_url = f'/users/{Test.user_one.id}/profile_feed/'
        endpoint_url = base_endpoint_url + \
            '?experiences=true' + \
            '&playlists=true' + \
            '&posts=true'
        response = self.client.get(endpoint_url)
        self.assertEqual(response.status_code, 200)
        continuation = response.data['continuation']
        all_results += response.data['results']
        seen_all = response.data['seen_all']

        # Make sure the test doesn't fail, this test should have
        # made more than 1 page of data
        self.assertFalse(seen_all)
        self.assertNotEqual(len(all_results), created_count)

        # Get any remaining pages from the continuation
        while not seen_all:
            endpoint_url = base_endpoint_url + \
                '?experiences=true' + \
                '&playlists=true' + \
                '&posts=true' + \
                f'&continuation={continuation}'
            response = self.client.get(endpoint_url)
            self.assertEqual(response.status_code, 200)
            seen_all = response.data['seen_all']
            all_results += response.data['results']

        seen_playlist_ids = []
        seen_experience_ids = []
        seen_post_ids = []

        for item in all_results:
            id = item['id']
            match item['model']:
                case 'Playlist':
                    self.assertTrue(id in playlist_ids)
                    self.assertTrue(id not in seen_playlist_ids)
                    seen_playlist_ids.append(id)
                case 'Experience':
                    self.assertTrue(id in experience_ids)
                    self.assertTrue(id not in seen_experience_ids)
                    seen_experience_ids.append(id)
                case 'Post':
                    self.assertTrue(id in post_ids)
                    self.assertTrue(id not in seen_post_ids)
                    seen_post_ids.append(id)

        seen_count = len(seen_playlist_ids) + len(seen_experience_ids) + len(seen_post_ids)
        self.assertEqual(created_count, seen_count)


    def test_profile_feed_accepts_and_completes(self):
        base_endpoint_url = f'/users/{Test.user_one.id}/profile_feed/'
        endpoint_url = base_endpoint_url + \
            '?experiences=true' + \
            '&playlists=true' + \
            '&posts=true' + \
            '&content_interactions=true'
        response = self.client.get(endpoint_url)
        self.assertEqual(response.status_code, 200)

        # Client wants to hide the fact that accepts happen to the Flutter app
        # Returns Bucket List Accepts
        # PlaylistAccept.objects.create(
        #     playlist=Test.playlist_one,
        #     user=Test.user_one)
        # endpoint_url = base_endpoint_url + \
        #     '?experiences=true' + \
        #     '&playlists=true' + \
        #     '&posts=true' + \
        #     '&content_interactions=true'
        # response = self.client.get(endpoint_url)
        # self.assertEqual(response.data['results'][0]['id'], Test.playlist_one.id)
        # self.assertIsNotNone(response.data['results'][0].get('accepted_at'))

        # Returns Bucket List Completes
        PlaylistCompletion.objects.create(
            playlist=Test.playlist_one,
            user=Test.user_one)
        endpoint_url = base_endpoint_url + \
            '?experiences=true' + \
            '&playlists=true' + \
            '&posts=true' + \
            '&content_interactions=true'
        response = self.client.get(endpoint_url)
        results = response.data['results']
        self.assertEqual(results[0]['id'], Test.playlist_one.id)
        self.assertIsNotNone(results[0].get('completed_at'))

        # Client wants to hide the fact that accepts happen to the Flutter app
        # Returns Experience Accepts
        # ExperienceAccept.objects.create(
        #     experience=Test.experience_one,
        #     user=Test.user_one)
        # endpoint_url = base_endpoint_url + \
        #     '?experiences=true' + \
        #     '&playlists=true' + \
        #     '&posts=true' + \
        #     '&content_interactions=true'
        # response = self.client.get(endpoint_url)
        # results = response.data['results']
        # self.assertEqual(results[0]['id'], Test.experience_one.id)
        # self.assertEqual(results[1]['id'], Test.playlist_one.id)
        # self.assertEqual(results[2]['id'], Test.playlist_one.id)
        # # The first item (most recent) should be the accept
        # self.assertIsNotNone(results[0].get('accepted_at'))
        # self.assertEqual(results[0]['model'], 'Experience')

        # Returns Experience Completes
        ExperienceCompletion.objects.create(
            experience=Test.experience_one,
            user=Test.user_one)
        endpoint_url = base_endpoint_url + \
            '?experiences=true' + \
            '&playlists=true' + \
            '&posts=true' + \
            '&content_interactions=true'
        response = self.client.get(endpoint_url)
        results = response.data['results']
        self.assertEqual(results[0]['id'], Test.experience_one.id)
        self.assertEqual(results[1]['id'], Test.playlist_one.id)
        # The first item (most recent) should be the completion
        self.assertIsNotNone(results[0].get('completed_at'))
        self.assertEqual(results[0]['model'], 'Experience')

        # Do not show if a user accepts their own content
        own_playlist = Playlist.objects.create(
            created_by=Test.user_one,
            name='playlist'
        )
        PlaylistAccept.objects.create(
            playlist=own_playlist,
            user=Test.user_one)
        endpoint_url = base_endpoint_url + \
            '?experiences=true' + \
            '&playlists=true' + \
            '&posts=true' + \
            '&content_interactions=true'
        response = self.client.get(endpoint_url)
        results = response.data['results']
        self.assertEqual(results[0]['id'], own_playlist.id)
        self.assertIsNone(results[0].get('completed_at'))
        own_experience = Experience.objects.create(
            created_by=Test.user_one,
            name='playlist')
        ExperienceAccept.objects.create(
            experience=own_experience,
            user=Test.user_one)
        endpoint_url = base_endpoint_url + \
            '?experiences=true' + \
            '&playlists=true' + \
            '&posts=true' + \
            '&content_interactions=true'
        response = self.client.get(endpoint_url)
        results = response.data['results']
        self.assertEqual(results[0]['id'], own_experience.id)
        self.assertIsNone(results[0].get('accepted_at'))
