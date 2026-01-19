import json
from rest_framework import status
from api.enums import Publicity
from rest_framework.authtoken.models import Token

from api.models import (
    Playlist,
    Experience,
    Post,
    User
)
from api.testing_overrides import GlobalTestCredentials, TestFiles
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    other_user: User
    playlist: Playlist
    experience: Experience
    post: Post
    playlist_post: Post
    experience_post: Post

    def setUpTestData():
        global_user: User = GlobalTestCredentials.user
        Test.other_user = User.objects.create(
            username='other_user',
            email='other_user@email.com',
            email_verified=True)

        Test.playlist = Playlist.objects.create(
            name='test_playlist',
            created_by=global_user)

        Test.experience = Experience.objects.create(
            name='test_experience',
            created_by=global_user)

        Test.post = Post.objects.create(
            name='post',
            text='post not attached to anything',
            created_by=global_user)

        Test.playlist_post = Post.objects.create(
            name='playlist test',
            text='test post for a playlist',
            created_by=global_user,
            playlist=Test.playlist)

        Test.experience_post = Post.objects.create(
            name = 'experience test',
            text = 'test post for a experience',
            created_by = global_user,
            experience = Test.experience)


    def setUp(self):
        super().setUp()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {GlobalTestCredentials.token}')

    def test_create_endpoint(self):
        pre_test_post_count = Post.objects.count()

        # No content post
        response = self.client.post('/posts/', {
            'json': json.dumps({
                'name': 'test_post_name',
                'text': 'test_playlist_two',
            })
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['model'], 'Post')

        current_post_count = Post.objects.count()
        self.assertEqual(
            current_post_count,
            pre_test_post_count + 1,
            msg=f'Current post count = {current_post_count}')

        # Experience post
        response = self.client.post('/posts/', {
            'json': json.dumps({
                'name': 'test_post_name',
                'text': 'test_post_text',
                'experience': Test.experience.id,
            })
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['text'], 'test_post_text')
        self.assertEqual(response.data['name'], 'test_post_name')
        self.assertEqual(response.data['experience'], Test.experience.id)
        self.assertEqual(response.data['model'], 'Post')

        current_post_count = Post.objects.count()
        self.assertEqual(
            current_post_count,
            pre_test_post_count + 2,
            msg=f'Current post count = {current_post_count}')

        # Playlist post
        response = self.client.post('/posts/', {
            'json': json.dumps({
                'name': 'test_post_name',
                'text': 'test_post_text',
                'playlist': Test.playlist.id,
            })
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['text'], 'test_post_text')
        self.assertEqual(response.data['name'], 'test_post_name')
        self.assertEqual(response.data['playlist'], Test.playlist.id)
        self.assertEqual(response.data['model'], 'Post')

        current_post_count = Post.objects.count()
        self.assertEqual(
            current_post_count,
            pre_test_post_count + 3,
            msg=f'Current post count = {current_post_count}')

        # POST invalid post (no text)
        response = self.client.post('/posts/', {
            'json': json.dumps({
                'name': 'test_post_name',
            })
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # POST invalid post (no name)
        response = self.client.post('/posts/', {
            'json': json.dumps({
                'text': 'test_post',
            })
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_update_model(self):
        # PUT valid post name
        response = self.client.put(f'/posts/{Test.post.id}/', {
            'json': json.dumps({
                'name': 'test_updated_post',
                'text': 'new_text',
                'replace_highlight_image': False,
                'replace_video': False,
            })
        })

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['name'], 'test_updated_post')
        updated_post : Post = Post.objects \
            .filter(id=Test.post.id).first()
        self.assertEqual(updated_post.name, 'test_updated_post')
        self.assertEqual(updated_post.text, 'new_text')

        # PUT invalid post no name included
        response = self.client.put(f'/posts/{Test.post.id}/', {
            'json': json.dumps({
                'text': 'new_text',
            })
        })
        self.assertEqual(response.status_code, 400)

        # PUT invalid post no text included
        response = self.client.put(f'/posts/{Test.post.id}/', {
            'json': json.dumps({
                'name': 'test_updated_post',
            })
        })
        self.assertEqual(response.status_code, 400)

        # PUT valid change experience
        response = self.client.put(f'/posts/{Test.post.id}/', {
            'json': json.dumps({
                'text': 'new_text',
                'name': 'test_updated_post',
                'experience': Test.experience.id,
            })
        })
        self.assertEqual(response.status_code, 202)
        updated_post : Post = Post.objects \
            .filter(id=Test.post.id).first()
        self.assertEqual(updated_post.experience.id, Test.experience.id)

        # PUT valid change playlist
        response = self.client.put(f'/posts/{Test.post.id}/', {
            'json': json.dumps({
                'text': 'new_text',
                'name': 'test_updated_post',
                'playlist': Test.playlist.id,
            })
        })
        self.assertEqual(response.status_code, 202)
        updated_post : Post = Post.objects \
            .filter(id=Test.post.id).first()
        self.assertEqual(updated_post.playlist.id, Test.playlist.id)

        # PUT invalid change both playlist and experience
        response = self.client.put(f'/posts/{Test.post.id}/', {
            'json': json.dumps({
                'text': 'new_text',
                'name': 'test_updated_post',
                'playlist': Test.playlist.id,
                'experience': Test.experience.id,
            })
        })
        self.assertEqual(response.status_code, 400)

        # PUT valid post as strings, not json
        # This is because the phone sends put requests with form data (all strings)
        # not json when uploading images.
        response = self.client.put(f'/posts/{Test.post.id}/', {
            'json': json.dumps({
                'name': 'test_updated_post',
                'text': 'test_updated_post_text',
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
        self.assertEqual(response.data['name'], 'test_updated_post')

        # PUT make sure it doesn't fail with attachments even though they are ignored
        response = self.client.put(f'/posts/{Test.post.id}/', {
            'json': json.dumps({
                'name': 'test_updated_post',
                'text': 'test_updated_post_text',
                'replace_highlight_image': False,
                'replace_video': False,
                'attachments': []
            })
        })
        self.assertEqual(response.status_code, 202)

        # PUT different user attempted to change post
        other_token = Token.objects.create(user=Test.other_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')
        response = self.client.put(f'/posts/{Test.post.id}/', {
            'json': json.dumps({
                'name': 'test_updated_post',
                'text': 'test_updated_post_text',
                'replace_highlight_image': False,
                'replace_video': False,
            })
        })
        self.assertEqual(response.status_code, 401)


    def test_retrieve_model(self):
        global_user: User = GlobalTestCredentials.user
        # GET valid playlist post
        response = self.client.get(f'/posts/{Test.playlist_post.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'playlist test')
        self.assertEqual(response.data['text'], 'test post for a playlist')
        self.assertEqual(response.data['created_by']['id'], global_user.id)
        self.assertEqual(response.data['created_by']['username'], global_user.username)
        self.assertEqual(response.data['playlist'], Test.playlist.id)

        # GET valid experience post
        response = self.client.get(f'/posts/{Test.experience_post.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'experience test')
        self.assertEqual(response.data['text'], 'test post for a experience')
        self.assertEqual(response.data['created_by']['id'], global_user.id)
        self.assertEqual(response.data['created_by']['username'], global_user.username)
        self.assertEqual(response.data['experience'], Test.experience.id)

        # GET invalid post
        response = self.client.get('/posts/-1/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_list(self):
        newestPost = Post.objects.create(
            name='post',
            text='post not attached to anything',
            created_by=Test.other_user)

        # GET list of posts in starting from most recent
        response = self.client.get('/posts/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(response.data['results'][0]['id'], newestPost.id)
        self.assertEqual(response.data['results'][0]['name'], newestPost.name)
        self.assertEqual(response.data['results'][0]['created_by']['id'], newestPost.created_by.id)

        # GET list of posts created by the global user
        response = self.client.get(f'/posts/?created_by={GlobalTestCredentials.user.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['results'][0]['id'], Test.experience_post.id)

    def test_mark_seen(self):
        global_user: User = GlobalTestCredentials.user
        pre_test_seen_count = global_user.seen_posts.count()

        with self.settings(SKIP_MARK_FOLLOW_FEED_SEEN=False):
            response = self.client.post(f'/posts/{Test.playlist_post.id}/mark_seen/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIsNone(response.data)

            current_seen_count = global_user.seen_posts.count()
            self.assertEqual(
                current_seen_count,
                pre_test_seen_count + 1)

            response = self.client.post(f'/posts/{Test.experience_post.id}/mark_seen/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIsNone(response.data)

            current_seen_count = global_user.seen_posts.count()
            self.assertEqual(
                current_seen_count,
                pre_test_seen_count + 2)


    def test_updated_experience_by_setting_nulls(self):
        response = self.client.post('/posts/', {
            'highlight_image': TestFiles.get_simple_uploaded_file('jpg'),
            'highlight_image_thumbnail': TestFiles.get_simple_uploaded_file('jpg'),
            'video': TestFiles.get_simple_uploaded_file('mp4'),
            'json': json.dumps({
                'name': 'name',
                'text': 'test text',
                'start_time': '2022-11-23T00:00:00.00Z',
                'end_time': '2022-12-23T00:00:00.00Z',
            })
        })
        self.assertEqual(response.status_code, 201)

        # Remove highlight_image, thumbnail, and video
        id = response.data['id']
        response = self.client.put(f'/posts/{id}/', data={
            'json': json.dumps({
                'name': 'name',
                'text': 'test text',
                'replace_highlight_image_thumbnail': True,
                'replace_highlight_image': True,
                'replace_video': True,
            })
        })
        self.assertEqual(response.status_code, 202)
        p: Post = Post.objects.filter(id=id).first()
        # images/videos will still be type ImageFieldFile/FieldFile, but their effective value is None
        # They raise a value error if None, since a ImageFieldFile: None has no url
        with self.assertRaises(ValueError):
            p.highlight_image.url
        with self.assertRaises(ValueError):
            p.highlight_image_thumbnail.url
        with self.assertRaises(ValueError):
            p.video.url
