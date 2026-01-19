import datetime
from rest_framework.authtoken.models import Token

from api.models import (
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
    token_one: Token
    token_two: Token

    def setUpTestData():
        Test.user_one = User.objects.create(
            username = 'test_user_one',
            email = 'testuserone@email.com',
            email_verified = False,
        )
        Test.user_two = User.objects.create(
            username = 'test_user_two',
            email = 'testusertwo@email.com',
            email_verified = True,
        )
        Test.user_three = User.objects.create(
            username = 'test_user_three',
            email = 'testuserthree@email.com',
            email_verified = True,
        )
        Test.token_one = Token.objects.create(user=Test.user_one)
        Test.token_two = Token.objects.create(user=Test.user_two)


    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_one}')


    def test_follow_feed(self):
        # Unverified user should 403
        response = self.client.get('/follow_feed/')
        self.assertEqual(response.status_code, 403)

        # Create an Experience for user_one
        user_one_experience: Experience = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.user_one)

        # Add some comments to user_one_experience
        Comment.objects.create(
            created_by = Test.user_two,
            text = 'this is the best experience!',
            experience = user_one_experience)
        Comment.objects.create(
            created_by = Test.user_three,
            text = 'this is the worst experience!',
            experience = user_one_experience)

        # Verified user should 200, but there shouldn't be any content yet
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.get('/follow_feed/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('continuation', response.data)
        self.assertEqual(response.data['experiences'], [])
        self.assertEqual(response.data['playlists'], [])
        response_posts: list[dict] = response.data['posts']
        self.assertEqual(response_posts, [])

        experience_posts = [p for p in response_posts if p['experience'] is not None]
        playlist_posts = [p for p in response_posts if p['playlist'] is not None]
        app_posts = [p for p in response_posts if p['playlist'] is None and p['experience'] is None]

        # Have user_two follow user_one
        response = self.client.post(f'/users/{Test.user_one.id}/follow/')
        self.assertEqual(response.status_code, 200)

        # Now that user_two is following user_one this should 200 and return the experience
        response = self.client.get('/follow_feed/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('continuation', response.data)

        response_posts: list[dict] = response.data['posts']
        experience_posts = [p for p in response_posts if p['model'] == 'ExperiencePost']
        playlist_posts = [p for p in response_posts if p['model'] == 'PlaylistPost']
        app_posts = [p for p in response_posts if p['model'] == 'Post']

        self.assertEqual(len(response.data['experiences']), 1)
        response_exp = response.data['experiences'][0]
        self.assertEqual(response_exp['name'], 'test_experience')
        self.assertEqual(response_exp['created_by']['id'], Test.user_one.id)
        self.assertEqual(response_exp['created_by']['username'], Test.user_one.username)
        self.assertEqual(response_exp['total_comments'], 2)
        self.assertEqual(response.data['playlists'], [])
        self.assertEqual(response_posts, [])

        # Create a experience post for user_one
        Post.objects.create(
            text = 'test_text',
            created_by = Test.user_one,
            experience = user_one_experience)

        # Should 200 and return the experience and post
        response = self.client.get('/follow_feed/')
        response_posts: list[dict] = response.data['posts']
        experience_posts = [p for p in response_posts if p['experience'] is not None]
        playlist_posts = [p for p in response_posts if p['playlist'] is not None]
        app_posts = [p for p in response_posts if p['playlist'] is None and p['experience'] is None]
        self.assertEqual(response.status_code, 200)
        self.assertIn('continuation', response.data)
        self.assertEqual(len(response.data['experiences']), 1)
        self.assertEqual(len(response.data['posts']), 1)
        response_exp = response.data['experiences'][0]
        self.assertEqual(response_exp['name'], 'test_experience')
        self.assertEqual(response_exp['created_by']['id'], Test.user_one.id)
        self.assertEqual(response_exp['created_by']['username'], Test.user_one.username)
        self.assertEqual(response_exp['total_comments'], 2)
        response_exp_post = experience_posts[0]
        self.assertEqual(response_exp_post['text'], 'test_text')
        self.assertEqual(response_exp_post['created_by']['id'], Test.user_one.id)
        self.assertEqual(response_exp_post['created_by']['username'], Test.user_one.username)
        self.assertEqual(response.data['playlists'], [])

        # Create a Playlist for user_one
        user_one_playlist: Playlist = Playlist.objects.create(
            name = 'test_playlist',
            created_by = Test.user_one)

        # Add a comment for user_one_playlist
        Comment.objects.create(
            created_by = Test.user_three,
            text = 'I like this playlist!',
            playlist = user_one_playlist)

        # Should 200 and return the experience and post
        response = self.client.get('/follow_feed/')
        self.assertEqual(response.status_code, 200)
        response_posts: list[dict] = response.data['posts']
        experience_posts = [p for p in response_posts if p['experience'] is not None]
        playlist_posts = [p for p in response_posts if p['playlist'] is not None]
        app_posts = [p for p in response_posts if p['playlist'] is None and p['experience'] is None]
        self.assertIn('continuation', response.data)
        self.assertEqual(len(response.data['experiences']), 1)
        self.assertEqual(len(response.data['playlists']), 1)
        self.assertEqual(len(response.data['posts']), 1)
        response_exp = response.data['experiences'][0]
        self.assertEqual(response_exp['name'], 'test_experience')
        self.assertEqual(response_exp['created_by']['id'], Test.user_one.id)
        self.assertEqual(response_exp['created_by']['username'], Test.user_one.username)
        self.assertEqual(response_exp['total_comments'], 2)
        response_bl = response.data['playlists'][0]
        self.assertEqual(response_bl['name'], 'test_playlist')
        self.assertEqual(response_bl['created_by']['id'], Test.user_one.id)
        self.assertEqual(response_bl['created_by']['username'], Test.user_one.username)
        self.assertEqual(response_bl['total_comments'], 1)
        response_exp_post = experience_posts[0]
        self.assertEqual(response_exp_post['text'], 'test_text')
        self.assertEqual(response_exp_post['created_by']['id'], Test.user_one.id)
        self.assertEqual(response_exp_post['created_by']['username'], Test.user_one.username)

        # Create a playlist post for user_three
        Post.objects.create(
            text = 'user_three_playlist_post',
            created_by = Test.user_three,
            playlist = user_one_playlist)

        # Have user_two follow user_three
        response = self.client.post(f'/users/{Test.user_three.id}/follow/')
        self.assertEqual(response.status_code, 200)

        # Should 200 and return the experience and post
        response = self.client.get('/follow_feed/')
        self.assertEqual(response.status_code, 200)
        response_posts: list[dict] = response.data['posts']
        experience_posts = [p for p in response_posts if p['experience'] is not None]
        playlist_posts = [p for p in response_posts if p['playlist'] is not None]
        app_posts = [p for p in response_posts if p['playlist'] is None and p['experience'] is None]
        self.assertIn('continuation', response.data)
        self.assertEqual(len(response.data['experiences']), 1)
        self.assertEqual(len(response.data['playlists']), 1)
        self.assertEqual(len(playlist_posts), 1)
        self.assertEqual(len(experience_posts), 1)
        self.assertEqual(len(app_posts), 0)
        response_exp = response.data['experiences'][0]
        self.assertEqual(response_exp['name'], 'test_experience')
        self.assertEqual(response_exp['created_by']['id'], Test.user_one.id)
        self.assertEqual(response_exp['created_by']['username'], Test.user_one.username)
        self.assertEqual(response_exp['total_comments'], 2)
        response_bl = response.data['playlists'][0]
        self.assertEqual(response_bl['name'], 'test_playlist')
        self.assertEqual(response_bl['created_by']['id'], Test.user_one.id)
        self.assertEqual(response_bl['created_by']['username'], Test.user_one.username)
        self.assertEqual(response_bl['total_comments'], 1)
        response_exp_post = experience_posts[0]
        self.assertEqual(response_exp_post['text'], 'test_text')
        self.assertEqual(response_exp_post['created_by']['id'], Test.user_one.id)
        self.assertEqual(response_exp_post['created_by']['username'], Test.user_one.username)
        response_pl_post = playlist_posts[0]
        self.assertEqual(response_pl_post['text'], 'user_three_playlist_post')
        self.assertEqual(response_pl_post['created_by']['id'], Test.user_three.id)
        self.assertEqual(response_pl_post['created_by']['username'], Test.user_three.username)

        # Create a experience post for user three
        user_three_post = Post.objects.create(
            text = 'user_three_experience_post',
            created_by = Test.user_three,
            experience = user_one_experience)

        # Add some comments to user_three_post
        Comment.objects.create(
            created_by = Test.user_two,
            text = 'I agree with this post',
            post = user_three_post)
        Comment.objects.create(
            created_by = Test.user_two,
            text = 'I am commenting twice!',
            post = user_three_post)
        Comment.objects.create(
            created_by = Test.user_two,
            text = 'I am commenting three times!',
            post = user_three_post)

        # Should 200 and return the experience and post
        response = self.client.get('/follow_feed/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('continuation', response.data)
        self.assertEqual(len(response.data['experiences']), 1)
        self.assertEqual(len(response.data['playlists']), 1)
        response_posts: list[dict] = response.data['posts']
        experience_posts = [p for p in response_posts if p['experience'] is not None]
        playlist_posts = [p for p in response_posts if p['playlist'] is not None]
        app_posts = [p for p in response_posts if p['playlist'] is None and p['experience'] is None]
        self.assertEqual(len(experience_posts), 2)
        self.assertEqual(len(playlist_posts), 1)
        response_exp = response.data['experiences'][0]
        self.assertEqual(response_exp['name'], 'test_experience')
        self.assertEqual(response_exp['created_by']['id'], Test.user_one.id)
        self.assertEqual(response_exp['created_by']['username'], Test.user_one.username)
        self.assertEqual(response_exp['total_comments'], 2)
        response_bl = response.data['playlists'][0]
        self.assertEqual(response_bl['name'], 'test_playlist')
        self.assertEqual(response_bl['created_by']['id'], Test.user_one.id)
        self.assertEqual(response_bl['created_by']['username'], Test.user_one.username)
        self.assertEqual(response_bl['total_comments'], 1)
        response_exp_post_2 = experience_posts[0]
        self.assertEqual(response_exp_post_2['text'], 'user_three_experience_post')
        self.assertEqual(response_exp_post_2['created_by']['id'], Test.user_three.id)
        self.assertEqual(response_exp_post_2['created_by']['username'], Test.user_three.username)
        self.assertEqual(response_exp_post_2['total_comments'], 3)
        response_exp_post_1 = experience_posts[1]
        self.assertEqual(response_exp_post_1['text'], 'test_text')
        self.assertEqual(response_exp_post_1['created_by']['id'], Test.user_one.id)
        self.assertEqual(response_exp_post_1['created_by']['username'], Test.user_one.username)
        response_pl_post = playlist_posts[0]
        self.assertEqual(response_pl_post['text'], 'user_three_playlist_post')
        self.assertEqual(response_pl_post['created_by']['id'], Test.user_three.id)
        self.assertEqual(response_pl_post['created_by']['username'], Test.user_three.username)

    def test_follow_feed_includes_own_content(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        experience: Experience = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.user_two)
        post: Post = Post.objects.create(
            name = 'post',
            text = 'text',
            created_by = Test.user_two)
        playlist = Playlist.objects.create(
            name='playlist',
            created_by = Test.user_two)
        response = self.client.get('/follow_feed/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(experience.id, (response.data['experiences'][0]['id']))
        self.assertEqual(post.id, (response.data['posts'][0]['id']))
        self.assertEqual(playlist.id, (response.data['playlists'][0]['id']))

    def test_follow_feed_includes_sampled_comments(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        experience: Experience = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.user_two)
        post: Post = Post.objects.create(
            name = 'post',
            text = 'text',
            created_by = Test.user_two)
        playlist = Playlist.objects.create(
            name='playlist',
            created_by = Test.user_two)

        Comment.objects.create(
            experience=experience,
            text='0',
            created_by=Test.user_one)
        popular_comment = Comment.objects.create(
            experience=experience,
            text='1',
            created_by=Test.user_one)
        popular_comment.likes.add(Test.user_one)
        last_experience_comment = Comment.objects.create(
            experience=experience,
            text='2',
            created_by=Test.user_one)

        Comment.objects.create(
            post=post,
            text='0',
            created_by=Test.user_one,
            created_at=datetime.datetime(2022, 1, 1))
        parent_comment = Comment.objects.create(
            post=post,
            text='2',
            created_by=Test.user_one)
        child_comment = Comment.objects.create(
            post=post,
            text='3',
            created_by=Test.user_one,
            parent=parent_comment)

        Comment.objects.create(
            playlist=playlist,
            text='0',
            created_by=Test.user_one)

        response = self.client.get('/follow_feed/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['playlists'][0]['sample_comments']), 1)
        # should not receive non-root comments
        post_comments = response.data['posts'][0]['sample_comments']
        post_comment_ids = [comment['id'] for comment in post_comments]
        self.assertEqual(len(post_comments), 2)
        self.assertNotIn(child_comment.id, post_comment_ids)

        # Should only receive a maximum of 2 comments.
        # Should be ordered by most likes, then most recent.
        experience_comments = response.data['experiences'][0]['sample_comments']
        experience_comment_ids = [comment['id'] for comment in experience_comments]
        self.assertEqual(experience_comment_ids, [popular_comment.id, last_experience_comment.id])
