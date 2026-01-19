import json
from rest_framework.authtoken.models import Token
from api.models.activity import Activity
from api.enums import ActivityType
from api.utils.mentioning import MentionUtils
from api.models import (
    Playlist,
    Experience,
    Post,
    User
)
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    user_doggydog  = User(email='test1@test.com', email_verified=True, username='doggydog')
    user_donna123  = User(email='test2@test.com', email_verified=True, username='donna123')
    user_karen5    = User(email='test3@test.com', email_verified=True, username='karen5')
    user_derek_123 = User(email='test4@test.com', email_verified=True, username='derek_123')
    user_unverified = User(email='test5@test.com', email_verified=False, username='unverified')
    playlist: Playlist
    experience: Experience
    playlist_post: Post
    token: Token

    def setUpTestData():
        User.objects.bulk_create([
            Test.user_doggydog,
            Test.user_donna123,
            Test.user_karen5,
            Test.user_derek_123,
            Test.user_unverified,
        ])
        Test.playlist = Playlist.objects.create(
            name = 'test Playlist',
            created_by = Test.user_doggydog)
        Test.experience = Experience.objects.create(
            name = 'test Experience',
            created_by = Test.user_donna123)
        Test.playlist_post = Post.objects.create(
            text = 'test Post for a Playlist',
            created_by = Test.user_karen5,
            playlist = Test.playlist)
        Test.token = Token.objects.create(user=Test.user_doggydog)

    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')

    def test_mention_in_comment(self):
        # POST comment with 2 mentions
        text = f"Hey <@{Test.user_donna123.id}> and <@{Test.user_karen5.id}>'s post"
        response = self.client.post(
            f'/posts/{Test.playlist_post.id}/comment/',
            { 'text': text},
            format='json')
        self.assertEqual(response.status_code, 201)
        comment: dict = response.data
        mentions: list[dict] = comment['mentions']
        self.assertEqual(len(mentions), 2)
        user_ids = [m['user_id'] for m in mentions]
        self.assertIn(Test.user_donna123.id, user_ids)
        self.assertIn(Test.user_karen5.id, user_ids)

        # GET comment should have 2 mentions
        response = self.client.get(f'/posts/{Test.playlist_post.id}/comments/')
        self.assertEqual(response.status_code, 200)
        comment: dict = response.data['results'][0]
        mentions: list[dict] = comment['mentions']
        self.assertEqual(len(mentions), 2)
        user_ids = [m['user_id'] for m in mentions]
        self.assertIn(Test.user_donna123.id, user_ids)
        self.assertIn(Test.user_karen5.id, user_ids)

    def test_mention_in_experience(self):
        description = f"Hey <@{Test.user_donna123.id}> and <@{Test.user_karen5.id}>'s post"
        # POST experience
        response = self.client.post('/experiences/', data={
            'json': json.dumps({
                'name': 'test_experience_two',
                'description': description,
            })
        })
        self.assertEqual(response.status_code, 201)
        experience_dict: dict = response.data
        self.assertEqual(experience_dict['description'], description)
        mentions = experience_dict['mentions']
        self.assertEqual(len(mentions), 2)
        user_ids = [m['user_id'] for m in mentions]
        self.assertIn(Test.user_donna123.id, user_ids)
        self.assertIn(Test.user_karen5.id, user_ids)
        experience_id = experience_dict['id']

        # GET experience
        response = self.client.get(f'/experiences/{experience_id}/')
        experience_dict: dict = response.data
        description = experience_dict['description']
        mentions = experience_dict['mentions']
        self.assertEqual(len(mentions), 2)
        user_ids = [m['user_id'] for m in mentions]
        self.assertIn(Test.user_donna123.id, user_ids)
        self.assertIn(Test.user_karen5.id, user_ids)


    def test_verified_users_mentioned_in_text(self):
        # No mentions empty string
        text = ''
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 0)

        # No mentions
        text = 'There are no mentions in this text.'
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 0)

        # No mentions with new lines
        text = '''
            There are no mentions in this
            text.
        '''
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 0)

        # Mention 1 real user
        text = ''.join([
            f"User <@{Test.user_doggydog.id}> is nice",
        ])
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 1)
        self.assertIn(Test.user_doggydog, users)

        # Mention 2 real users
        text = f"Hey <@{Test.user_donna123.id}> and <@{Test.user_karen5.id}>'s post"
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 2)
        self.assertIn(Test.user_donna123, users)
        self.assertIn(Test.user_karen5, users)

        # Invalid tagging, tags should be <@1234>
        text = 'I never new @donna123 thought that about @karen5'
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 0)

        # Mention real users no spaces
        text = f'<@{Test.user_donna123.id}><@{Test.user_karen5.id}>'
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 2)
        self.assertIn(Test.user_donna123, users)
        self.assertIn(Test.user_karen5, users)

        # Mention real users with no space and new lines
        text = f'''
            How many do you want <@{Test.user_derek_123.id}><@{Test.user_karen5.id}>
            and <@{Test.user_donna123.id}> or anyone
            else
        '''
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 3)
        self.assertIn(Test.user_derek_123, users)
        self.assertIn(Test.user_karen5, users)
        self.assertIn(Test.user_donna123, users)

        # Double mention karen5
        text = f'''
            How many do you want <@{Test.user_derek_123.id}><@{Test.user_karen5.id}>
            or anyone else <@{Test.user_karen5.id}>
        '''
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 2)
        Test.user_derek_123
        self.assertIn(Test.user_derek_123, users)
        self.assertIn(Test.user_karen5, users)

        # Double mention karen5 with lots of special characters
        text = f'''
            How many do you want !<@{Test.user_derek_123.id}><@{Test.user_karen5.id}>123
            or anyone else <@{Test.user_karen5.id}> 32 $ !@#$% #$^&
        '''
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 2)
        Test.user_derek_123
        self.assertIn(Test.user_derek_123, users)
        self.assertIn(Test.user_karen5, users)

        # @ symbol before tag
        text = f'@<@{Test.user_karen5.id}>'
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 1)
        self.assertIn(Test.user_karen5, users)

        # number after tag
        text = f'<@{Test.user_karen5.id}>5'
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 1)
        self.assertIn(Test.user_karen5, users)

        # Don't tag unverified
        text = f'<@{Test.user_unverified.id}>'
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 0)

        # Don't tag unverified
        text = f'Hey there <@{Test.user_unverified.id}>'
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 0)

        # Don't tag unverified
        text = f'Hey there <@{Test.user_unverified.id}> and <@{Test.user_derek_123.id}>'
        users = MentionUtils.verified_users_mentioned_in_text(text)
        self.assertEqual(len(users), 1)
        self.assertIn(Test.user_derek_123, users)

    def comment_mentions_generates_activities(self):
        self.assertFalse(Activity.objects.filter(
                user=Test.user_donna123,
                related_user=Test.user_doggydog,
                type=ActivityType.MENTIONED_COMMENT,
                post=Test.playlist_post).exists())
        text = f"Hey <@{Test.user_donna123.id}> post"
        response = self.client.post(
            f'/posts/{Test.playlist_post.id}/comment/',
            { 'text': text},
            format='json')
        self.assertTrue(Activity.objects.filter(
                user=Test.user_donna123,
                related_user=Test.user_doggydog,
                type=ActivityType.MENTIONED_COMMENT,
                comment__id=response.data['id'],
                post=Test.playlist_post).exists())

    def experience_mentions_generates_activities(self):
        self.assertFalse(Activity.objects.filter(
                user=Test.user_derek_123,
                related_user=Test.user_doggydog,
                type=ActivityType.MENTIONED_EXPERIENCE).exists())
        description = f"Hey <@{Test.user_derek_123.id}>"
        response = self.client.post('/experiences/', {
            'name': 'test_experience_three',
            'description': description,
        }, format='json')
        self.assertTrue(Activity.objects.filter(
                user=Test.user_derek_123,
                related_user=Test.user_doggydog,
                type=ActivityType.MENTIONED_EXPERIENCE,
                experience__id=response.data['id']).exists())

    def playlist_mentions_generates_activities(self):
        self.assertFalse(Activity.objects.filter(
                user=Test.user_derek_123,
                related_user=Test.user_doggydog,
                type=ActivityType.MENTIONED_EXPERIENCE).exists())
        description = f"Hey <@{Test.user_derek_123.id}>"
        response = self.client.post('/playlist/', {
            'name': 'test_playlist_two',
            'description': description,
        }, format='json')
        self.assertTrue(Activity.objects.filter(
                user=Test.user_derek_123,
                related_user=Test.user_doggydog,
                type=ActivityType.MENTIONED_EXPERIENCE,
                playlist__id=response.data['id']).exists())

    def post_mentions_generates_activities(self):
        self.assertFalse(Activity.objects.filter(
                user=Test.user_derek_123,
                related_user=Test.user_doggydog,
                type=ActivityType.MENTIONED_POST).exists())
        description = f"Hey <@{Test.user_derek_123.id}>"
        response = self.client.post('/post/', {
            'name': 'test_playlist_two',
            'description': description,
        }, format='json')
        self.assertTrue(Activity.objects.filter(
                user=Test.user_derek_123,
                related_user=Test.user_doggydog,
                type=ActivityType.MENTIONED_POST,
                post__id=response.data['id']).exists())
