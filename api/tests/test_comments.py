from rest_framework.authtoken.models import Token

from api.models import (
    Activity,
    Playlist,
    Experience,
    Comment,
    Post,
    User
)
from api.enums import ActivityType
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    user_one: User
    user_two: User
    playlist: Playlist
    experience: Experience
    post: Post
    token_one: Token
    token_two: Token

    def setUpTestData():
        Test.user_one = User.objects.create(
            username = 'test_user_one',
            email = 'testuserone@email.com',
            email_verified = True)
        Test.user_two = User.objects.create(
            username = 'test_user_two',
            email = 'testusertwo@email.com',
            email_verified = True)
        Test.playlist = Playlist.objects.create(
            name = 'test_playlist',
            created_by = Test.user_one)
        Test.experience = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.user_one)
        Test.post = Post.objects.create(
            text = 'test post for a playlist',
            created_by = Test.user_one,
            playlist = Test.playlist)
        Test.token_one = Token.objects.create(user=Test.user_one)
        Test.token_two = Token.objects.create(user=Test.user_two)


    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')


    def test_playlist_comment_generates_activity(self):
        self.assertFalse(Activity.objects.filter(
            playlist=Test.playlist,
            user=Test.user_one,
            related_user=Test.user_two,
            type=ActivityType.COMMENTED_PLAYLIST).exists())
        self.client.post(f'/playlists/{Test.playlist.id}/comment/', {
            'text': 'test comment'
        }, format='json')
        self.assertTrue(Activity.objects.filter(
            playlist=Test.playlist,
            user=Test.user_one,
            related_user=Test.user_two,
            type=ActivityType.COMMENTED_PLAYLIST).exists())


    def test_experience_comment_generates_activity(self):
        self.assertFalse(Activity.objects.filter(
            experience=Test.experience,
            user=Test.user_one,
            related_user=Test.user_two,
            type=ActivityType.COMMENTED_EXPERIENCE).exists())
        self.client.post(f'/experiences/{Test.experience.id}/comment/', {
            'text': 'test comment'
        }, format='json')
        self.assertTrue(Activity.objects.filter(
            experience=Test.experience,
            user=Test.user_one,
            related_user=Test.user_two,
            type=ActivityType.COMMENTED_EXPERIENCE).exists())


    def test_post_comment_generates_activity(self):
        self.assertFalse(Activity.objects.filter(
            post=Test.post,
            user=Test.user_one,
            related_user=Test.user_two,
            type=ActivityType.COMMENTED_POST).exists())
        response = self.client.post(f'/posts/{Test.post.id}/comment/', {
            'text': 'test comment'
        }, format='json')
        self.assertTrue(Activity.objects.filter(
            user=Test.user_one,
            related_user=Test.user_two,
            post=Test.post,
            related_comment=response.data['id'],
            type=ActivityType.COMMENTED_POST).exists())


    def test_comment_comment_generates_activity(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_one}')
        self.client.post(f'/experiences/{Test.experience.id}/comment/', {
            'text': 'test parent comment'
        }, format='json')
        parent_comment: Comment = Comment.objects.get(text='test parent comment')
        self.assertFalse(Activity.objects.filter(
            user=Test.user_one,
            related_user=Test.user_two,
            comment=parent_comment,
            type=ActivityType.COMMENTED_COMMENT).exists())
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        self.client.post(f'/comments/{parent_comment.id}/comment/', {
            'text': 'test child comment'
        }, format='json')
        child_comment: Comment = Comment.objects.get(text='test child comment')
        self.assertTrue(Activity.objects.filter(
            user=Test.user_one,
            related_user=Test.user_two,
            comment=parent_comment,
            related_comment=child_comment,
            type=ActivityType.COMMENTED_COMMENT).exists())


    def test_own_comment_does_not_generate_activity(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_one}')
        self.assertFalse(Activity.objects.filter(
            experience=Test.experience,
            user=Test.user_one,
            related_user=Test.user_two,
            type=ActivityType.COMMENTED_EXPERIENCE).exists())
        response = self.client.post(f'/experiences/{Test.experience.id}/comment/', {
            'text': 'test comment'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(Activity.objects.filter(
            experience=Test.experience,
            user=Test.user_one,
            related_user=Test.user_two,
            type=ActivityType.COMMENTED_EXPERIENCE).exists())


    def test_child_comment_is_created_with_correct_fields(self):
        # Create a comment on a playlist
        response = self.client.post(f'/playlists/{Test.playlist.id}/comment/', {
            'text': 'test parent comment on playlist'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('created_by', response.data)
        self.assertTrue(bool(response.data['created_by']['id']))
        self.assertEqual(response.data['text'], 'test parent comment on playlist')
        pl_parent_comment = Comment.objects.get(text='test parent comment on playlist')

        # Create a comment on a experience
        response = self.client.post(f'/experiences/{Test.experience.id}/comment/', {
            'text': 'test parent comment on experience'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'test parent comment on experience')
        c_parent_comment = Comment.objects.get(text='test parent comment on experience')

        # Create a comment on a post
        response = self.client.post(f'/posts/{Test.post.id}/comment/', {
            'text': 'test parent comment on post'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'test parent comment on post')
        p_parent_comment = Comment.objects.get(text='test parent comment on post')

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_one}')

        # Create a child comment of the playlist's comment
        response = self.client.post(f'/comments/{pl_parent_comment.id}/comment/', {
            'text': 'test child comment on playlist parent comment'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'test child comment on playlist parent comment')
        pl_child_comment = Comment.objects.get(text='test child comment on playlist parent comment')
        self.assertEqual(pl_child_comment.parent, pl_parent_comment)
        self.assertEqual(pl_child_comment.playlist, pl_parent_comment.playlist)
        # Ensure this child's playlist field is not none and its experience and post fields are none
        self.assertIsNotNone(pl_child_comment.playlist)
        self.assertIsNone(pl_child_comment.experience)
        self.assertIsNone(pl_child_comment.post)

        # Create a child comment of the experience's comment
        response = self.client.post(f'/comments/{c_parent_comment.id}/comment/', {
            'text': 'test child comment on experience parent comment'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'test child comment on experience parent comment')
        c_child_comment = Comment.objects.get(text='test child comment on experience parent comment')
        self.assertEqual(c_child_comment.parent, c_parent_comment)
        self.assertEqual(c_child_comment.experience, c_parent_comment.experience)
        # Ensure this child's experience field is not none and its playlist and post fields are none
        self.assertIsNotNone(c_child_comment.experience)
        self.assertIsNone(c_child_comment.playlist)
        self.assertIsNone(c_child_comment.post)

        # Create a child comment of the post's comment
        response = self.client.post(f'/comments/{p_parent_comment.id}/comment/', {
            'text': 'test child comment on post parent comment'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'test child comment on post parent comment')
        p_child_comment = Comment.objects.get(text='test child comment on post parent comment')
        self.assertEqual(p_child_comment.parent, p_parent_comment)
        self.assertEqual(p_child_comment.post, p_parent_comment.post)
        # Ensure this child's post field is not none and its playlist and experience fields are none
        self.assertIsNotNone(p_child_comment.post)
        self.assertIsNone(p_child_comment.playlist)
        self.assertIsNone(p_child_comment.experience)


    def test_playlist_comments(self):
        response = self.client.get(f'/playlists/{Test.playlist.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 0)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_one}')
        prev_total_count = Test.playlist.total_comments
        response = self.client.post(f'/playlists/{Test.playlist.id}/comment/', {
            'text': 'test comment'
        }, format='json')
        Test.playlist.refresh_from_db()
        Total_count = Test.playlist.total_comments
        self.assertEqual(Total_count, prev_total_count + 1)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'test comment')

        response = self.client.get(f'/playlists/{Test.playlist.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['text'], 'test comment')

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.post(f'/playlists/{Test.playlist.id}/comment/', {
            'text': 'another test comment'
        }, format='json')
        comment_id_for_later = response.data['id']
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'another test comment')

        response = self.client.get(f'/playlists/{Test.playlist.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual('test comment', response.data['results'][0]['text'])
        self.assertEqual('another test comment', response.data['results'][1]['text'])

        # Requesting nonexistent pages should 404
        response = self.client.get(f'/playlists/{Test.playlist.id}/comments/?page=-1')
        self.assertEqual(response.status_code, 404)
        response = self.client.get(f'/playlists/{Test.playlist.id}/comments/?page=0')
        self.assertEqual(response.status_code, 404)
        response = self.client.get(f'/playlists/{Test.playlist.id}/comments/?page=2')
        self.assertEqual(response.status_code, 404)

        # Requesting page 1 should be functionally the same as without a page query param
        response = self.client.get(f'/playlists/{Test.playlist.id}/comments/?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual('test comment', response.data['results'][0]['text'])
        self.assertEqual('another test comment', response.data['results'][1]['text'])

        # Edit comment
        edit_text = 'this playlist comment has been edited'
        comment_to_edit = Comment.objects.get(pk=comment_id_for_later)
        self.assertNotEqual(comment_to_edit.text, edit_text)
        self.assertFalse(comment_to_edit.edited)
        response = self.client.put(
            f'/playlists/{Test.playlist.id}/comment/?comment_id={comment_id_for_later}',
            {'text': edit_text}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['text'], edit_text)
        comment_to_edit.refresh_from_db()
        self.assertEqual(comment_to_edit.text, edit_text)
        self.assertTrue(comment_to_edit.edited)

        # Delete comment
        response = self.client.get(f'/playlists/{Test.playlist.id}/?details=true')
        self.assertEqual(response.data['total_comments'], 2)
        response = self.client.delete(
            f'/playlists/{Test.playlist.id}/comment/?comment_id={comment_id_for_later}')
        self.assertEqual(response.status_code, 204)
        with self.assertRaises(Comment.DoesNotExist):
            comment_to_edit.refresh_from_db()
        response = self.client.get(f'/playlists/{Test.playlist.id}/?details=true')
        self.assertEqual(response.data['total_comments'], 1)


    def test_experience_comments(self):
        response = self.client.get(f'/experiences/{Test.experience.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 0)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_one}')
        response = self.client.post(f'/experiences/{Test.experience.id}/comment/', {
            'text': 'test comment'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'test comment')

        response = self.client.get(f'/experiences/{Test.experience.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['text'], 'test comment')

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.post(f'/experiences/{Test.experience.id}/comment/', {
            'text': 'another test comment'
        }, format='json')
        comment_id_for_later = response.data['id']
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'another test comment')

        response = self.client.get(f'/experiences/{Test.experience.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual('test comment', response.data['results'][0]['text'])
        self.assertEqual('another test comment', response.data['results'][1]['text'])

        # Requesting nonexistent pages should 404
        response = self.client.get(f'/experiences/{Test.experience.id}/comments/?page=-1')
        self.assertEqual(response.status_code, 404)
        response = self.client.get(f'/experiences/{Test.experience.id}/comments/?page=0')
        self.assertEqual(response.status_code, 404)
        response = self.client.get(f'/experiences/{Test.experience.id}/comments/?page=2')
        self.assertEqual(response.status_code, 404)

        # Requesting page 1 should be functionally the same as without a page query param
        response = self.client.get(f'/experiences/{Test.experience.id}/comments/?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual('test comment', response.data['results'][0]['text'])
        self.assertEqual('another test comment', response.data['results'][1]['text'])

        # Edit comment
        edit_text = 'this experience comment has been edited'
        comment_to_edit = Comment.objects.get(pk=comment_id_for_later)
        self.assertNotEqual(comment_to_edit.text, edit_text)
        self.assertFalse(comment_to_edit.edited)
        response = self.client.put(
            f'/experiences/{Test.experience.id}/comment/?comment_id={comment_id_for_later}',
            {'text': edit_text}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['text'], edit_text)
        comment_to_edit.refresh_from_db()
        self.assertEqual(comment_to_edit.text, edit_text)
        self.assertTrue(comment_to_edit.edited)

        # Delete comment
        response = self.client.get(f'/experiences/{Test.experience.id}/?details=true')
        self.assertEqual(response.data['total_comments'], 2)
        response = self.client.delete(
            f'/experiences/{Test.experience.id}/comment/?comment_id={comment_id_for_later}')
        self.assertEqual(response.status_code, 204)
        with self.assertRaises(Comment.DoesNotExist):
            comment_to_edit.refresh_from_db()
        response = self.client.get(f'/experiences/{Test.experience.id}/?details=true')
        self.assertEqual(response.data['total_comments'], 1)


    def test_comment_comments(self):
        response = self.client.post(f'/playlists/{Test.playlist.id}/comment/', {
            'text': 'test parent comment'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'test parent comment')

        parent: Comment = Comment.objects.get(text='test parent comment')

        response = self.client.get(f'/comments/{parent.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 0)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_one}')
        response = self.client.post(f'/comments/{parent.id}/comment/', {
            'text': 'test child comment'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'test child comment')

        response = self.client.get(f'/comments/{parent.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['text'], 'test child comment')

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.post(f'/comments/{parent.id}/comment/', {
            'text': 'another test child comment'
        }, format='json')
        comment_id_for_later = response.data['id']
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'another test child comment')

        response = self.client.get(f'/comments/{parent.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual('test child comment', response.data['results'][0]['text'])
        self.assertEqual('another test child comment', response.data['results'][1]['text'])

        # Requesting nonexistent pages should 404
        response = self.client.get(f'/comments/{parent.id}/comments/?page=-1')
        self.assertEqual(response.status_code, 404)
        response = self.client.get(f'/comments/{parent.id}/comments/?page=0')
        self.assertEqual(response.status_code, 404)
        response = self.client.get(f'/comments/{parent.id}/comments/?page=2')
        self.assertEqual(response.status_code, 404)

        # Requesting page 1 should be functionally the same as without a page query param
        response = self.client.get(f'/comments/{parent.id}/comments/?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual('test child comment', response.data['results'][0]['text'])
        self.assertEqual('another test child comment', response.data['results'][1]['text'])

        # Edit comment
        edit_text = 'this child comment has been edited'
        comment_to_edit = Comment.objects.get(pk=comment_id_for_later)
        self.assertNotEqual(comment_to_edit.text, edit_text)
        self.assertFalse(comment_to_edit.edited)
        response = self.client.put(
            f'/comments/{parent.id}/comment/?comment_id={comment_id_for_later}',
            {'text': edit_text}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['text'], edit_text)
        comment_to_edit.refresh_from_db()
        self.assertEqual(comment_to_edit.text, edit_text)
        self.assertTrue(comment_to_edit.edited)

        # Delete comment
        response = self.client.get(f'/comments/{parent.id}/comments/')
        self.assertEqual(len(response.data['results']), 2)
        response = self.client.delete(
            f'/comments/{parent.id}/comment/?comment_id={comment_id_for_later}')
        self.assertEqual(response.status_code, 204)
        with self.assertRaises(Comment.DoesNotExist):
            comment_to_edit.refresh_from_db()
        response = self.client.get(f'/comments/{parent.id}/comments/')
        self.assertEqual(len(response.data['results']), 1)


    def test_post_comments(self):
        response = self.client.get(f'/posts/{Test.post.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 0)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_one}')
        response = self.client.post(f'/posts/{Test.post.id}/comment/', {
            'text': 'test comment'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'test comment')

        response = self.client.get(f'/posts/{Test.post.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['text'], 'test comment')

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.post(f'/posts/{Test.post.id}/comment/', {
            'text': 'another test comment'
        }, format='json')
        comment_id_for_later = response.data['id']
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'another test comment')

        response = self.client.get(f'/posts/{Test.post.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual('test comment', response.data['results'][0]['text'])
        self.assertEqual('another test comment', response.data['results'][1]['text'])

        # Requesting nonexistent pages should 404
        response = self.client.get(f'/posts/{Test.post.id}/comments/?page=-1')
        self.assertEqual(response.status_code, 404)
        response = self.client.get(f'/posts/{Test.post.id}/comments/?page=0')
        self.assertEqual(response.status_code, 404)
        response = self.client.get(f'/posts/{Test.post.id}/comments/?page=2')
        self.assertEqual(response.status_code, 404)

        # Requesting page 1 should be functionally the same as without a page query param
        response = self.client.get(f'/posts/{Test.post.id}/comments/?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual('test comment', response.data['results'][0]['text'])
        self.assertEqual('another test comment', response.data['results'][1]['text'])

        # Edit comment
        edit_text = 'this post comment has been edited'
        comment_to_edit = Comment.objects.get(pk=comment_id_for_later)
        self.assertNotEqual(comment_to_edit.text, edit_text)
        self.assertFalse(comment_to_edit.edited)
        response = self.client.put(
            f'/posts/{Test.post.id}/comment/?comment_id={comment_id_for_later}',
            {'text': edit_text}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['text'], edit_text)
        comment_to_edit.refresh_from_db()
        self.assertEqual(comment_to_edit.text, edit_text)
        self.assertTrue(comment_to_edit.edited)

        # Delete comment
        response = self.client.get(f'/posts/{Test.post.id}/?details=true')
        self.assertEqual(response.data['total_comments'], 2)
        response = self.client.delete(
            f'/posts/{Test.post.id}/comment/?comment_id={comment_id_for_later}')
        self.assertEqual(response.status_code, 204)
        with self.assertRaises(Comment.DoesNotExist):
            comment_to_edit.refresh_from_db()
        response = self.client.get(f'/posts/{Test.post.id}/?details=true')
        self.assertEqual(response.data['total_comments'], 1)


    def test_retrieving_comments(self):
        parent_comment = Comment.objects.create(
            created_by = self.user_one,
            experience = self.experience,
            text = 'parent test comment',
        )
        comment_two = Comment.objects.create(
            created_by = self.user_one,
            experience = self.experience,
            text = 'second test comment',
        )
        child_comment = Comment.objects.create(
            created_by = self.user_one,
            experience = Test.experience,
            parent = parent_comment,
            text = 'child test comment',
        )

        # Experiences, Playlists, and Posts should not return child comments
        response = self.client.get(f'/experiences/{self.experience.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['id'], parent_comment.id)
        self.assertEqual(response.data['results'][1]['id'], comment_two.id)

        # Getting a comment's comments should return child comments
        response = self.client.get(f'/comments/{parent_comment.id}/comments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], child_comment.id)
