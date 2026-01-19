from rest_framework.authtoken.models import Token

from api.models import (
    Activity,
    Playlist,
    Experience,
    Comment,
    Post,
    User,
)
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    user_one: User
    user_two: User
    user_three: User
    user_four: User
    user_five: User
    playlist: Playlist
    experience: Experience
    comment: Comment
    post: Post
    post_two: Post
    token_one: Token
    token_two: Token
    token_three: Token
    token_four: Token
    token_five: Token

    def setUpTestData():
        Test.user_one = User.objects.create(
            username='test_user_one',
            email='testuserone@email.com',
            email_verified=True)
        Test.user_two = User.objects.create(
            username='test_user_two',
            email='testusertwo@email.com',
            email_verified=True)
        Test.user_three = User.objects.create(
            username='test_user_three',
            email='testuserthree@email.com',
            email_verified=True)
        Test.user_four = User.objects.create(
            username='test_user_four',
            email='testuserfour@email.com',
            email_verified=True)
        Test.user_five = User.objects.create(
            username='test_user_five',
            email='testuserfive@email.com',
            email_verified=True)
        Test.playlist = Playlist.objects.create(
            name='test_playlist',
            created_by=Test.user_two)
        Test.experience = Experience.objects.create(
            name='test_experience',
            created_by=Test.user_two)
        Test.comment = Comment.objects.create(
            created_by=Test.user_two,
            text='test comment',
            playlist=Test.playlist)
        Test.post = Post.objects.create(
            created_by=Test.user_one,
            text='test post',
            experience=Test.experience)
        Test.post_two = Post.objects.create(
            created_by=Test.user_two,
            text='test post',
            experience=Test.experience)
        Test.token_one = Token.objects.create(user=Test.user_one)
        Test.token_two = Token.objects.create(user=Test.user_two)
        Test.token_three = Token.objects.create(user=Test.user_three)
        Test.token_four = Token.objects.create(user=Test.user_four)
        Test.token_five = Token.objects.create(user=Test.user_five)


    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_one}')


    def test_playlist_total_likes(self):
        response = self.client.get(f'/playlists/{Test.playlist.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_likes'], 0)

        # Have user one like the playlist, assert 201 created response
        response = self.client.post(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 201)

        # Have user two like the playlist, assert 201 created response
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.post(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 201)

        # Have user three like the playlist, assert 201 created response
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_three}')
        response = self.client.post(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 201)

        # Have user four like the playlist, assert 201 created response
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_four}')
        response = self.client.post(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 201)

        response = self.client.get(f'/playlists/{Test.playlist.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_likes'], 4)


    def test_experience_total_likes(self):
        response = self.client.get(f'/experiences/{Test.experience.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_likes'], 0)

        # Have user one like the experience, assert 201 created response
        response = self.client.post(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 201)

        # Have user two like the experience, assert 201 created response
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.post(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 201)

        # Have user three like the experience, assert 201 created response
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_three}')
        response = self.client.post(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 201)

        # Have user four like the experience, assert 201 created response
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_four}')
        response = self.client.post(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 201)

        # Have user five like the experience, assert 201 created response
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_five}')
        response = self.client.post(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 201)

        response = self.client.get(f'/experiences/{Test.experience.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_likes'], 5)


    def test_comment_total_likes(self):
        response = self.client.get(f'/playlists/{Test.playlist.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['total_likes'], 0)

        # Have user one like the comment, assert 201 created response
        response = self.client.post(f'/comments/{Test.comment.id}/like/')
        self.assertEqual(response.status_code, 201)

        # Have user two like the comment, assert 201 created response
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.post(f'/comments/{Test.comment.id}/like/')
        self.assertEqual(response.status_code, 201)

        # Have user three like the comment, assert 201 created response
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_three}')
        response = self.client.post(f'/comments/{Test.comment.id}/like/')
        self.assertEqual(response.status_code, 201)

        response = self.client.get(f'/playlists/{Test.playlist.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['total_likes'], 3)


    def test_post_total_likes(self):
        response = self.client.get(f'/posts/{Test.post.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_likes'], 0)

        # Have user one like the post, assert 201 created response
        response = self.client.post(f'/posts/{Test.post.id}/like/')
        self.assertEqual(response.status_code, 201)

        # Have user two like the post, assert 201 created response
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.post(f'/posts/{Test.post.id}/like/')
        self.assertEqual(response.status_code, 201)

        response = self.client.get(f'/posts/{Test.post.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_likes'], 2)


    def test_playlist_likes_crud(self):
        response = self.client.get(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data)

        response = self.client.post(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data)

        # POST 400s when there is already a like
        response = self.client.post(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 400)

        response = self.client.get(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data)

        response = self.client.delete(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(response.data)

        response = self.client.get(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data)

        # DELETE 404s when there is no like to delete
        response = self.client.delete(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 404)


    def test_experience_likes_crud(self):
        response = self.client.get(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data)

        response = self.client.post(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data)

        # POST 400s when there is already a like
        response = self.client.post(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 400)

        response = self.client.get(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data)

        response = self.client.delete(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(response.data)

        response = self.client.get(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data)

        # DELETE 404s when there is no like to delete
        response = self.client.delete(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 404)


    def test_comment_likes_crud(self):
        response = self.client.get(f'/comments/{Test.comment.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data)

        response = self.client.post(f'/comments/{Test.comment.id}/like/')
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data)

        # POST 400s when there is already a like
        response = self.client.post(f'/comments/{Test.comment.id}/like/')
        self.assertEqual(response.status_code, 400)

        response = self.client.get(f'/comments/{Test.comment.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data)

        response = self.client.delete(f'/comments/{Test.comment.id}/like/')
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(response.data)

        response = self.client.get(f'/comments/{Test.comment.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data)

        # DELETE 404s when there is no like to delete
        response = self.client.delete(f'/comments/{Test.comment.id}/like/')
        self.assertEqual(response.status_code, 404)


    def test_post_likes_crud(self):
        response = self.client.get(f'/posts/{Test.post.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data)

        response = self.client.post(f'/posts/{Test.post.id}/like/')
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data)

        # POST 400s when there is already a like
        response = self.client.post(f'/posts/{Test.post.id}/like/')
        self.assertEqual(response.status_code, 400)

        response = self.client.get(f'/posts/{Test.post.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data)

        response = self.client.delete(f'/posts/{Test.post.id}/like/')
        self.assertEqual(response.status_code, 204)
        self.assertIsNone(response.data)

        response = self.client.get(f'/posts/{Test.post.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data)

        # DELETE 404s when there is no like to delete
        response = self.client.delete(f'/posts/{Test.post.id}/like/')
        self.assertEqual(response.status_code, 404)


    def test_like_activities(self):
        # Create a post activity when liking
        response = self.client.post(f'/posts/{Test.post_two.id}/like/')
        self.assertEqual(response.status_code, 201)
        activity = Activity.objects.filter(
            user=Test.post_two.created_by,
            related_user=Test.user_one,
            post=Test.post_two)
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity[0].user, Test.post_two.created_by)
        self.assertEqual(activity[0].related_user, Test.user_one)
        self.assertEqual(activity[0].post, Test.post_two)

        # Delete the activity when removing the like
        response = self.client.delete(f'/posts/{Test.post_two.id}/like/')
        self.assertEqual(response.status_code, 204)
        activity = Activity.objects.filter(
            user=Test.post_two.created_by,
            related_user=Test.user_one,
            post=Test.post_two)
        self.assertFalse(activity.exists())

        # Create a experience activity when liking
        response = self.client.post(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 201)
        activity = Activity.objects.filter(
            user=Test.experience.created_by,
            related_user=Test.user_one,
            experience=Test.experience)
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity[0].user, Test.experience.created_by)
        self.assertEqual(activity[0].related_user, Test.user_one)
        self.assertEqual(activity[0].experience, Test.experience)

        # Delete the activity when removing the like
        response = self.client.delete(f'/experiences/{Test.experience.id}/like/')
        self.assertEqual(response.status_code, 204)
        activity = Activity.objects.filter(
            user=Test.experience.created_by,
            related_user=Test.user_one,
            experience=Test.experience)
        self.assertFalse(activity.exists())

        # Create a playlist activity when liking
        response = self.client.post(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 201)
        activity = Activity.objects.filter(
            user=Test.playlist.created_by,
            related_user=Test.user_one,
            playlist=Test.playlist)
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity[0].user, Test.playlist.created_by)
        self.assertEqual(activity[0].related_user, Test.user_one)
        self.assertEqual(activity[0].playlist, Test.playlist)

        # Delete the activity when removing the like
        response = self.client.delete(f'/playlists/{Test.playlist.id}/like/')
        self.assertEqual(response.status_code, 204)
        activity = Activity.objects.filter(
            user=Test.playlist.created_by,
            related_user=Test.user_one,
            playlist=Test.playlist)
        self.assertFalse(activity.exists())

        # Create a comment activity when liking
        response = self.client.post(f'/comments/{Test.comment.id}/like/')
        self.assertEqual(response.status_code, 201)
        activity = Activity.objects.filter(
            user=Test.comment.created_by,
            related_user=Test.user_one,
            comment=Test.comment)
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity[0].user, Test.comment.created_by)
        self.assertEqual(activity[0].related_user, Test.user_one)
        self.assertEqual(activity[0].comment, Test.comment)

        # Delete the activity when removing the like
        response = self.client.delete(f'/comments/{Test.comment.id}/like/')
        self.assertEqual(response.status_code, 204)
        activity = Activity.objects.filter(
            user=Test.comment.created_by,
            related_user=Test.user_one,
            comment=Test.comment)
        self.assertFalse(activity.exists())

        # Don't create and activity for liking one's own content
        response = self.client.post(f'/posts/{Test.post.id}/like/')
        self.assertEqual(response.status_code, 201)
        activity = Activity.objects.filter(
            user=Test.post.created_by,
            related_user=Test.user_one,
            post=Test.post)
        self.assertEqual(len(activity), 0)


    def test_retrieve_liking_users(self):
        # Order of experience likes creation 1, 2, 5, 4, 3
        Test.experience.likes.add(Test.user_one)
        Test.experience.likes.add(Test.user_two)
        Test.experience.likes.add(Test.user_five)
        Test.experience.likes.add(Test.user_four)
        Test.experience.likes.add(Test.user_three)

        response = self.client.get(f'/experiences/{Test.experience.id}/liking_users/')
        self.assertEqual(response.status_code, 200)
        # users should be in the reverse order of like creation.
        user_ids = [user['id']for user in response.data['results']]
        expected_id_order = [
            Test.user_three.id,
            Test.user_four.id,
            Test.user_five.id,
            Test.user_two.id,
            Test.user_one.id,
        ]
        self.assertEqual(user_ids, expected_id_order)

        Test.playlist.likes.add(Test.user_one)
        Test.playlist.likes.add(Test.user_two)
        response = self.client.get(f'/playlists/{Test.playlist.id}/liking_users/')
        self.assertEqual(response.status_code, 200)
        # users should be in the reverse order of like creation.
        user_ids = [user['id']for user in response.data['results']]
        expected_id_order = [Test.user_two.id, Test.user_one.id]
        self.assertEqual(user_ids, expected_id_order)

        Test.post.likes.add(Test.user_one)
        Test.post.likes.add(Test.user_two)
        response = self.client.get(f'/posts/{Test.post.id}/liking_users/')
        self.assertEqual(response.status_code, 200)
        # users should be in the reverse order of like creation.
        user_ids = [user['id']for user in response.data['results']]
        expected_id_order = [Test.user_two.id, Test.user_one.id]
        self.assertEqual(user_ids, expected_id_order)

        Test.comment.likes.add(Test.user_one)
        Test.comment.likes.add(Test.user_two)
        response = self.client.get(f'/comments/{Test.comment.id}/liking_users/')
        self.assertEqual(response.status_code, 200)
        # users should be in the reverse order of like creation.
        user_ids = [user['id']for user in response.data['results']]
        expected_id_order = [Test.user_two.id, Test.user_one.id]
        self.assertEqual(user_ids, expected_id_order)
