import json
from django.core.cache import cache
from uuid import uuid4
from rest_framework.authtoken.models import Token

from api.models import (
    Playlist,
    Experience,
    Post,
    User
)
from api.utils.categories import CategoryContentContinuation
from api.utils.follow_feed import FollowContinuation
from api.utils.profile_feed import ProfileFeedContinuation
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    user: User
    total_count: int
    expected_cache_timeout: int
    token: Token

    def setUpTestData():
        Test.user = User.objects.create(
            username = 'test_user',
            email = 'testuserone@email.com',
            email_verified = True,
        )
        Test.total_count = 50
        playlists_to_create = []
        experiences_to_create = []
        posts_to_create = []
        for i in range(Test.total_count):
            experiences_to_create.append(Experience(
                name=f"test_playlist_{i}",
                created_by=Test.user))
            playlists_to_create.append(Playlist(
                name=f"test_playlist_{i}",
                created_by=Test.user))
            posts_to_create.append(Post(
                text=f'test_post_{i}',
                created_by=Test.user))
        Experience.objects.bulk_create(experiences_to_create)
        Playlist.objects.bulk_create(playlists_to_create)
        Post.objects.bulk_create(posts_to_create)
        Test.expected_cache_timeout = 3600 # One hour in seconds
        Test.token = Token.objects.create(user=Test.user)


    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')


    def test_follow_continuation(self):
        random_token = str(uuid4())
        continuation = FollowContinuation(Test.user, random_token, False)
        self.assertEqual(continuation.cache_timeout, Test.expected_cache_timeout)
        self.assertEqual(continuation.token, random_token)
        self.assertEqual(continuation.user.id, Test.user.id)
        self.assertEqual(continuation.cache_key, f'follow_feed_{random_token}')
        self.assertEqual(continuation.sent_experiences, [])
        self.assertEqual(continuation.sent_playlists, [])
        self.assertEqual(continuation.sent_posts, [])

        cached = json.loads(continuation.get_cache())
        self.assertEqual(cached['sent_experiences'], [])
        self.assertEqual(cached['sent_playlists'], [])
        self.assertEqual(cached['sent_posts'], [])

        experiences = Experience.objects.all()
        playlists = Playlist.objects.all()
        posts = Post.objects.all()

        continuation.sent_experiences = [c.id for c in experiences]
        continuation.sent_playlists = [pl.id for pl in playlists]
        continuation.sent_posts = [p.id for p in posts]
        continuation.set_cache()

        cached = json.loads(continuation.get_cache())
        self.assertEqual(len(cached['sent_experiences']), Test.total_count)
        self.assertEqual(len(cached['sent_playlists']), Test.total_count)
        self.assertEqual(len(cached['sent_posts']), Test.total_count)

        continuation.refresh_cache()

        cached = json.loads(continuation.get_cache())
        self.assertEqual(cached['sent_experiences'], [])
        self.assertEqual(cached['sent_playlists'], [])
        self.assertEqual(cached['sent_posts'], [])

        # assert that cache is cleaned up
        self.assertTrue(cache.delete(continuation.cache_key))


    def test_category_continuation(self):
        random_token = str(uuid4())
        continuation = CategoryContentContinuation(random_token)
        # continuation.debug_print()
        self.assertEqual(continuation.cache_timeout, Test.expected_cache_timeout)
        self.assertEqual(continuation.token, random_token)
        self.assertEqual(continuation.cache_key, f'category_content_{random_token}')
        self.assertEqual(continuation.sent_experiences, [])
        self.assertEqual(continuation.sent_playlists, [])
        self.assertEqual(continuation.sent_posts, [])

        cached = json.loads(continuation.get_cache())
        self.assertEqual(cached['sent_experiences'], [])
        self.assertEqual(cached['sent_playlists'], [])
        self.assertEqual(cached['sent_posts'], [])

        experiences = Experience.objects.all()
        playlists = Playlist.objects.all()
        posts = Post.objects.all()

        continuation.sent_experiences = [c.id for c in experiences]
        continuation.sent_playlists = [pl.id for pl in playlists]
        continuation.sent_posts = [p.id for p in posts]
        continuation.set_cache()

        cached = json.loads(continuation.get_cache())
        self.assertEqual(len(cached['sent_experiences']), Test.total_count)
        self.assertEqual(len(cached['sent_playlists']), Test.total_count)
        self.assertEqual(len(cached['sent_posts']), Test.total_count)

        # assert that cache is cleaned up
        self.assertTrue(cache.delete(continuation.cache_key))


    def test_profile_feed_continuation(self):
        random_token = str(uuid4())
        continuation = ProfileFeedContinuation(Test.user, random_token)
        self.assertEqual(continuation.token, random_token)
        self.assertEqual(continuation.user.id, Test.user.id)
        self.assertEqual(continuation.cache_key, f'profile_feed_{random_token}')
        self.assertEqual(continuation.sent_experiences, [])
        self.assertEqual(continuation.sent_playlists, [])
        self.assertEqual(continuation.sent_posts, [])

        cached = json.loads(continuation.get_cache())
        self.assertEqual(cached['sent_experiences'], [])
        self.assertEqual(cached['sent_playlists'], [])
        self.assertEqual(cached['sent_posts'], [])

        experiences = Experience.objects.all()
        playlists = Playlist.objects.all()
        posts = Post.objects.all()

        continuation.sent_experiences = [c.id for c in experiences]
        continuation.sent_playlists = [pl.id for pl in playlists]
        continuation.sent_posts = [p.id for p in posts]
        continuation.set_cache()

        cached = json.loads(continuation.get_cache())
        self.assertEqual(len(cached['sent_experiences']), Test.total_count)
        self.assertEqual(len(cached['sent_playlists']), Test.total_count)
        self.assertEqual(len(cached['sent_posts']), Test.total_count)

        continuation.refresh_cache()

        cached = json.loads(continuation.get_cache())
        self.assertEqual(cached['sent_experiences'], [])
        self.assertEqual(cached['sent_playlists'], [])
        self.assertEqual(cached['sent_posts'], [])

        # assert that cache is cleaned up
        self.assertTrue(cache.delete(continuation.cache_key))
