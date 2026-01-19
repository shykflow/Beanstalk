import pytz
from django.utils import timezone
from rest_framework.authtoken.models import Token
from api.enums import ActivityType

from api.models import User, UserFollow
from api.models.activity import Activity
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    user_1: User
    user_2: User
    user_3: User
    user_1_follow_2: UserFollow
    token: Token

    # Ran before all tests only once.
    def setUpTestData():
        now = timezone.datetime.now(tz=pytz.timezone("UTC"))
        Test.user_1 = User.objects.create(
            username = 'user_1',
            email = 'user_1@email.com',
            email_verified = True,
        )
        Test.token = Token.objects.create(user=Test.user_1)
        Test.user_2 = User.objects.create(
            username = 'user_2',
            email = 'user_2@email.com',
            email_verified = True,
        )
        Token.objects.create(user=Test.user_2)
        Test.user_3 = User.objects.create(
            username = 'user_3',
            email = 'user_3@email.com',
            email_verified = True,
        )
        # All 3 users follow each other, except User3 who only follows User1
        Test.user_1_follow_2 = UserFollow.objects.create(
            user = Test.user_1,
            followed_user = Test.user_2,
            created_at = now,
        )
        UserFollow.objects.create(
            user = Test.user_1,
            followed_user = Test.user_3,
            created_at = now,
        )
        UserFollow.objects.create(
            user = Test.user_2,
            followed_user = Test.user_1,
            created_at = now,
        )
        UserFollow.objects.create(
            user = Test.user_2,
            followed_user = Test.user_3,
            created_at = now,
        )
        UserFollow.objects.create(
            user = Test.user_3,
            followed_user = Test.user_1,
            created_at = now,
        )


    # Ran before each test.
    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')


    def test_user_follow_count_retrieval(self):
        response = self.client.get(f'/users/{self.user_2.id}/?include_relationship_data=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.user_2.id)
        self.assertEqual(response.data['follows_viewer'], True)
        self.assertEqual(response.data['follower_count'], 1)
        self.assertEqual(response.data['common_outgoing_follows_count'], 1)
        self.assertEqual(response.data['commonly_followed_by_count'], 0)
        self.assertEqual(len(response.data['sampled_common_outgoing_follow_users']), 1)
        self.assertEqual(response.data['sampled_common_outgoing_follow_users'][0]['id'], self.user_3.id)


    def test_user_list_follow_count_retrieval(self):
        response = self.client.get(f'/users/?users={self.user_2.id},{self.user_3.id}&include_relationship_data=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(response.data[0]['id'] == self.user_2.id or response.data[1]['id'] == self.user_2.id)
        self.assertTrue(response.data[0]['id'] == self.user_3.id or response.data[1]['id'] == self.user_3.id)
        self.assertNotEqual(response.data[0]['id'], response.data[1]['id'])

        self.assertEqual(response.data[0]['follows_viewer'], True)
        self.assertEqual(response.data[1]['follows_viewer'], True)
        self.assertTrue(response.data[0]['follower_count'] == 2 or response.data[1]['follower_count'] == 2)
        self.assertTrue(response.data[0]['follower_count'] == 1 or response.data[1]['follower_count'], 1)
        self.assertNotEqual(response.data[0]['follower_count'], response.data[1]['follower_count'])


    def test_follow(self):
        Test.user_1_follow_2.delete()
        response = self.client.post(f'/users/{self.user_2.id}/follow/')
        self.assertEqual(response.status_code, 200)
        follow = UserFollow.objects.filter(user=self.user_1, followed_user=self.user_2).first()
        self.assertNotEqual(follow, None)

        response = self.client.post('/users/-1/follow/')
        self.assertEqual(response.status_code, 404)


    def test_unfollow(self):
        response = self.client.post(f'/users/{self.user_2.id}/unfollow/')
        self.assertEqual(response.status_code, 204)
        follow = UserFollow.objects.filter(user=self.user_1, followed_user=self.user_2).first()
        self.assertEqual(follow, None)

        response = self.client.post('/users/-1/unfollow/')
        self.assertEqual(response.status_code, 204)


    def test_follow_generates_activity(self):
        UserFollow.objects.filter(
            user = Test.user_1,
            followed_user = Test.user_2,).delete()
        self.assertFalse(Activity.objects.filter(
            user=Test.user_2,
            type=ActivityType.FOLLOW_NEW,
            related_user=Test.user_1).exists())
        self.client.post(f'/users/{self.user_2.id}/follow/')
        self.assertTrue(Activity.objects.filter(
            user=Test.user_2,
            type=ActivityType.FOLLOW_NEW,
            related_user=Test.user_1).exists())


    def test_user_follows_retrieve(self):
        users = []
        for i in range(18):
            user = User()
            user.username = f'generated-user-{i}'
            user.email = f'generated-user-{i}@email.com'
            users.append(user)
        User.objects.bulk_create(users)
        for user in users:
            Test.user_2.follows.add(user)
        response = self.client.get(f'/users/{self.user_2.id}/following/?page=1')
        self.assertEqual(response.status_code, 200)
        # Results are ordered by the most recent follows, in this case
        # that is the reverse order of user creation
        # The mutual follows should be first
        self.assertEqual(self.user_3.id, response.data['results'][0]['id'])
        self.assertTrue(response.data['results'][0]['followed_by_viewer'])
        users.reverse()
        for i, user in enumerate(users):
            # if i == 0 or i == len(users) -1: continue
            self.assertEqual(user.id, response.data['results'][i + 1]['id'])
            self.assertFalse(response.data['results'][i + 1]['followed_by_viewer'])
        self.assertEqual(Test.user_1.id, response.data['results'][-1]['id'])


    def test_user_followed_by_retrieve(self):
        users = []
        for i in range(19):
            user = User()
            user.username = f'generated-user-{i}'
            user.email = f'generated-user-{i}@email.com'
            users.append(user)
        # that they were followed in
        User.objects.bulk_create(users)
        # the first user will be a mutual follower
        UserFollow.objects.create(
            user=self.user_1,
            followed_user=users[0])
        for user in users:
            UserFollow.objects.create(
                user=user,
                followed_user=self.user_2)
        response = self.client.get(f'/users/{self.user_2.id}/followed_by/?page=1')
        self.assertEqual(response.status_code, 200)
        # Results are ordered by the most recently acquired followers, in this case
        # that is the reverse order of user creation
        # The mutual followers should be first
        self.assertEqual(users[0].id, response.data['results'][0]['id'])
        self.assertTrue(response.data['results'][0]['followed_by_viewer'])
        users.reverse()
        for i, user in enumerate(users):
            # Skip first and last
            if i == 0 or i == len(users) -1: continue
            self.assertEqual(user.id, response.data['results'][i + 1]['id'])
            self.assertFalse(response.data['results'][i + 1]['followed_by_viewer'])
        self.assertEqual(Test.user_1.id, response.data['results'][-1]['id'])

