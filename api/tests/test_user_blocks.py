import pytz
from django.utils import timezone
from rest_framework.authtoken.models import Token
from django.test import override_settings

from api.models import (
    User,
    UserBlock,
    Experience,
    Post,
    Playlist,
    Comment,
    UserFollow,
)
from api.enums import CustomHttpStatusCodes
from . import SilenceableAPITestCase

# Avoid calling sendbird for blocks
@override_settings(SENDBIRD_ENABLE_MESSAGING=False,)
class Test(SilenceableAPITestCase):
    user_1: User
    token: Token
    blocked_user: User
    blocking_user: User
    user_1_block_2: UserBlock
    blocking_user_block_1: UserBlock
    experience: Experience

    # Ran before all tests only once.
    def setUpTestData():
        now = timezone.datetime.now(tz=pytz.timezone("UTC"))
        Test.user_1 = User.objects.create(
            username = 'user_1',
            email = 'user_1@email.com',
            email_verified = True,
        )
        Test.token = Token.objects.create(user=Test.user_1)
        Test.blocked_user = User.objects.create(
            username = 'blocked_user',
            email = 'blocked_user@email.com',
            email_verified = True,
        )
        Token.objects.create(user=Test.blocked_user)
        Test.blocking_user = User.objects.create(
            username = 'blocking_user',
            email = 'blocking_user@email.com',
            email_verified = True,
        )
        Test.user_1_block_2 = UserBlock.objects.create(
            user = Test.user_1,
            blocked_user = Test.blocked_user,
            created_at = now,
        )
        Test.blocking_user_block_1 = UserBlock.objects.create(
            user = Test.blocking_user,
            blocked_user = Test.user_1,
            created_at = now,
        )
        Test.experience = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.blocking_user,)


    # Ran before each test.
    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')


    def testUserBlockRetrieval(self):
        now = timezone.datetime.now(tz=pytz.timezone("UTC"))
        UserBlock.objects.create(
            user = Test.user_1,
            blocked_user = Test.blocking_user,
            created_at = now,
        )
        response = self.client.get(f'/users/list_blocked/')
        assert response.status_code == 200
        contains_id_2 = False
        contains_id_3 = False
        contains_id_1 = False
        for userMap in response.data:
            if contains_id_2 == False:
                contains_id_2 = userMap['id'] == self.blocked_user.id
            if contains_id_3 == False:
                contains_id_3 = userMap['id'] == self.blocking_user.id
            if contains_id_1 == False:
                contains_id_1 = userMap['id'] == self.user_1.id
        assert contains_id_2
        assert contains_id_3
        assert not contains_id_1


    def test_block(self):
        Test.user_1_block_2.delete()
        response = self.client.post(f'/users/{self.blocked_user.id}/block/')
        assert response.status_code == 200
        Test.user_1_block_2 = UserBlock.objects.filter(user=self.user_1, blocked_user=self.blocked_user).first()
        assert Test.user_1_block_2 is not None
        response = self.client.post('/users/-1/block/')
        assert response.status_code == 404

        # Dont block yourself
        response = self.client.post(f'/users/{self.user_1.id}/block/')
        assert response.status_code == 400

    def test_unblock(self):
        response = self.client.post(f'/users/{self.blocked_user.id}/unblock/')
        assert response.status_code == 204
        block = UserBlock.objects.filter(user=self.user_1, blocked_user=self.blocked_user).first()
        assert block is None

        response = self.client.post('/users/-1/unblock/')
        assert response.status_code == 204

    def test_playlist_block(self):
        playlist_blocked: Playlist = Playlist.objects.create(
            name = 'test_playlist',
            created_by = Test.blocking_user,
        )
        playlist_blocking: Playlist = Playlist.objects.create(
            name = 'test_playlist',
            created_by = Test.blocked_user,
        )
        response = self.client.get(f'/playlists/{playlist_blocked.id}/')
        assert response.status_code == 404
        response = self.client.get(f'/playlists/{playlist_blocking.id}/')
        assert response.status_code == 404

    def test_experience_block(self):
        experience_blocked: Experience = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.blocking_user)
        experience_blocking: Experience = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.blocked_user)
        response = self.client.get(f'/experiences/{experience_blocked.id}/')
        assert response.status_code == 404
        response = self.client.get(f'/experiences/{experience_blocking.id}/')
        assert response.status_code == 404

    def test_post_block(self):
        post_blocked: Post = Post.objects.create(
            text = 'test post for a experience',
            created_by = Test.blocking_user,
            experience = Test.experience)
        post_blocking: Post = Post.objects.create(
            text = 'test post for a experience',
            created_by = Test.blocked_user,
            experience= Test.experience)
        response = self.client.get(f'/posts/{post_blocked.id}/')
        assert response.status_code == 404
        response = self.client.get(f'/posts/{post_blocking.id}/')
        assert response.status_code == 404


    def test_comment_blocks(self):
        now = timezone.datetime.now(tz=pytz.timezone("UTC"))
        post: Post = Post.objects.create(
            text = 'test',
            created_by = Test.user_1,
            experience = Test.experience)
        unblocked_comment: Comment = Comment.objects.create(
            text = 'test',
            post = post,
            created_by = Test.user_1,
            created_at = now)
        blocked_comment_comment : Comment = Comment.objects.create(
            text = 'test',
            parent = unblocked_comment,
            created_by = Test.blocking_user,
            created_at = now)
        blocked_comment: Comment = Comment.objects.create(
            text = 'test',
            post = post,
            created_by = Test.blocking_user,
            created_at = now)
        blocking_comment: Comment = Comment.objects.create(
            text = 'test',
            post = post,
            created_by = Test.blocked_user,
            created_at = now)
        response = self.client.get(f'/posts/{post.id}/comments/', {
            'text': 'test comment'
        }, format='json')
        assert len(response.data['results']) == 1


    def test_follow_blocked(self):
        UserBlock.objects.filter(user=Test.user_1, blocked_user=Test.blocked_user).first().delete()
        UserFollow.objects.create(
            user=Test.user_1,
            followed_user=Test.blocked_user)
        UserFollow.objects.create(
            user=Test.blocked_user,
            followed_user=Test.user_1)

        # bi-directionally unfollow when blocking
        response = self.client.post(f'/users/{Test.blocked_user.id}/block/')
        assert response.status_code == 200
        Test.user_1_block_2 = UserBlock.objects.filter(user=Test.user_1, blocked_user=Test.blocked_user).first()
        assert Test.user_1_block_2 is not None
        follow = UserFollow.objects.filter(user=Test.user_1, followed_user=Test.blocked_user).first()
        assert follow is None
        follow = UserFollow.objects.filter(user=Test.blocked_user, followed_user=Test.user_1).first()
        assert follow is None

        # dont allow following blocked or blocking users
        response = self.client.post(f'/users/{Test.blocked_user.id}/follow/')
        self.assertEqual(response.status_code,
            CustomHttpStatusCodes.HTTP_486_YOU_BLOCKED_USER)
        self.assertFalse(UserFollow.objects.filter(
            user=Test.user_1,
            followed_user=Test.blocking_user).exists())
        response = self.client.post(f'/users/{Test.blocking_user.id}/follow/')
        self.assertEqual(response.status_code,
            CustomHttpStatusCodes.HTTP_485_USER_BLOCKED_YOU)

    def test_user_lookup_blocked(self):
        response = self.client.get('/users/search/?q=blocked_user')
        assert response.data == []
        response = self.client.get('/users/search/?q=blocking_user')
        assert response.data == []

        response = self.client.get(f'/users/{Test.blocked_user.id}/?include_relationship_data=true')
        assert response.data['blocked'] == True
        response = self.client.get(f'/users/{Test.blocking_user.id}/?include_relationship_data=true')
        assert response.data['blocked'] == False

        response = self.client.get(f'/users/?users={Test.blocking_user.id},{Test.blocked_user.id}&include_relationship_data=true')
        assert len(response.data) == 2
        has_blocked_user = False
        has_non_blocked_user = False
        for map in response.data:
            if map['blocked'] == False:
                has_non_blocked_user = True
            else:
                has_blocked_user = True
        assert has_blocked_user
        assert has_non_blocked_user
