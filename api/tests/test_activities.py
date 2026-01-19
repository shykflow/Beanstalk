from django.forms import ValidationError
from rest_framework.authtoken.models import Token
from django.core.management import call_command

from api.models import (
    Activity,
    AggregateActivity,
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
    user_three: User
    activity_one: Activity
    activity_two: Activity
    token: Token

    def setUpTestData():
        Test.user_one = User.objects.create(
            username = 'test_user_one',
            email = 'testuserone@email.com',
            email_verified = True,
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
        Test.activity_one = Activity.objects.create(
            user = Test.user_one,
            type = ActivityType.FOLLOW_NEW,
            related_user = Test.user_two,
        )
        Test.activity_two = Activity.objects.create(
            user = Test.user_one,
            type = ActivityType.FOLLOW_NEW,
            related_user = Test.user_three,
        )
        Test.token = Token.objects.create(user=Test.user_one)


    # Ran before each test.
    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')


    def test_unseen_count_and_mark_all_seen(self):
        response = self.client.get('/activities/unseen_count/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 2)

        Activity.objects.create(
            user = Test.user_one,
            type = ActivityType.FOLLOW_ACCEPTED,
            related_user = Test.user_two,
        )

        response = self.client.get('/activities/unseen_count/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 3)

        response = self.client.post('/activities/mark_all_seen/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data)

        response = self.client.get('/activities/unseen_count/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 0)


    def test_sending_unnecessary_body_does_not_interfere(self):
        unnecessary_data = {
            'test_bool': True,
            'test_int': -1,
            'test_float': -2.5,
            'test_str': 'this string is just for testing purposes',
        }
        response = self.client.get('/activities/unseen_count/', unnecessary_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 2)

        response = self.client.post('/activities/mark_all_seen/', unnecessary_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data)

        response = self.client.get('/activities/unseen_count/', unnecessary_data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 0)


    def test_list_aggregated_and_unaggregated(self):
        user_one_experience: Experience = Experience.objects.create(
            created_by = Test.user_one,
            name = 'user_one_experience',
            description = 'test_description')

        response = self.client.get('/activities/list_aggregated/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

        response = self.client.get('/activities/list_unaggregated/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['type'], ActivityType.FOLLOW_NEW)
        self.assertEqual(response.data[1]['type'], ActivityType.FOLLOW_NEW)

        # marking seen no longer immediately alters aggregates or changes activities
        response = self.client.post('/activities/mark_all_seen/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data)

        aggregate = AggregateActivity.objects.create(
            user = Test.user_one,
            experience = user_one_experience,
            type = ActivityType.ACCEPTED_EXPERIENCE,
            related_user = Test.user_two)
        response = self.client.get('/activities/list_unaggregated/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['type'], ActivityType.FOLLOW_NEW)
        self.assertEqual(response.data[1]['type'], ActivityType.FOLLOW_NEW)

        response = self.client.get('/activities/list_aggregated/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['type'], ActivityType.ACCEPTED_EXPERIENCE)


    def test_non_follow_activities_are_aggregated(self):
        user_one_experience: Experience = Experience.objects.create(
            created_by = Test.user_one,
            name = 'user_one_experience',
            description = 'test_description')

        Activity.objects.create(
            user = Test.user_one,
            experience = user_one_experience,
            type = ActivityType.ACCEPTED_EXPERIENCE,
            related_user = Test.user_two)

        Activity.objects.create(
            user = Test.user_one,
            experience = user_one_experience,
            type = ActivityType.ACCEPTED_EXPERIENCE,
            related_user = Test.user_three)

        response = self.client.get('/activities/unseen_count/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, 4)

        response = self.client.post('/activities/mark_all_seen/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data)

        call_command('aggregate_activities')

        aggregated_activity: AggregateActivity = AggregateActivity.objects.get(
            user=Test.user_one,
            type=ActivityType.ACCEPTED_EXPERIENCE)

        response = self.client.get('/activities/list_unaggregated/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

        response = self.client.get('/activities/list_aggregated/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['user'], aggregated_activity.user.id)
        self.assertEqual(response.data[0]['count'], aggregated_activity.count)
        self.assertEqual(response.data[0]['experience'], aggregated_activity.experience.id)
        self.assertEqual(response.data[0]['type'], aggregated_activity.type)


    def test_aggregate_count(self):
        user_four: User = User.objects.create(
            username = 'test_user_four',
            email = 'testuserfour@email.com',
            email_verified = True)
        user_one_experience: Experience = Experience.objects.create(
            created_by = Test.user_one,
            name = 'user_one_experience',
            description = 'test_description')
        Activity.objects.create(
            user = Test.user_one,
            experience = user_one_experience,
            type = ActivityType.COMPLETED_EXPERIENCE,
            related_user = Test.user_two,
            seen = True)
        Activity.objects.create(
            user = Test.user_one,
            experience = user_one_experience,
            type = ActivityType.COMPLETED_EXPERIENCE,
            related_user = Test.user_three,
            seen = True)
        # Not seen, should not aggregate
        activity_three = Activity.objects.create(
            user = Test.user_one,
            experience = user_one_experience,
            type = ActivityType.COMPLETED_EXPERIENCE,
            related_user = user_four)
        call_command('aggregate_activities')

        aggregate = AggregateActivity.objects.get(
            type=ActivityType.COMPLETED_EXPERIENCE,
            user=Test.user_one)
        self.assertEqual(aggregate.count, 2)

        activity_three.seen = True
        activity_three.save()

        # Not seen
        Activity.objects.create(
            user = Test.user_one,
            experience = user_one_experience,
            type = ActivityType.COMPLETED_EXPERIENCE,
            related_user = user_four)

        call_command('aggregate_activities')

        aggregate.refresh_from_db()
        self.assertEqual(aggregate.count, 3)


    def test_activity_clean(self):
        test_activity = Activity(user=Test.user_one, type=ActivityType.FOLLOW_NEW)

        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.related_user = Test.user_two

        test_activity.type = ActivityType.MENTIONED_EXPERIENCE
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.MENTIONED_PLAYLIST
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.MENTIONED_EXPERIENCE_STACK
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.MENTIONED_POST
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.MENTIONED_COMMENT
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.LIKED_EXPERIENCE
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.LIKED_PLAYLIST
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.LIKED_EXPERIENCE_STACK
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.LIKED_POST
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.LIKED_COMMENT
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.COMMENTED_EXPERIENCE
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.COMMENTED_PLAYLIST
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.COMMENTED_EXPERIENCE_STACK
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.COMMENTED_POST
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.COMMENTED_COMMENT
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.ACCEPTED_EXPERIENCE
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.COMPLETED_EXPERIENCE
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.ACCEPTED_PLAYLIST
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.COMPLETED_PLAYLIST
        with self.assertRaises(ValidationError):
            test_activity.clean()

        # Should not raise
        test_activity.type = ActivityType.FOLLOW_NEW
        test_activity.clean()
        test_activity.type = ActivityType.FOLLOW_ACCEPTED
        test_activity.clean()
        test_activity.type = ActivityType.FOLLOW_REQUEST
        test_activity.clean()

        test_activity.type = ActivityType.ADDED_TO_YOUR_PLAYLIST
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.REMOVED_FROM_PLAYLIST
        with self.assertRaises(ValidationError):
            test_activity.clean()

        test_activity.type = ActivityType.ADDED_YOUR_EXPERIENCE_TO_PLAYLIST
        with self.assertRaises(ValidationError):
            test_activity.clean()


    def test_unseen_activity_counts(self):
        response = self.client.get('/activities/unseen_activity_counts/')
        assert response.status_code == 200
        assert response.data[0]['type'] == 500
        assert response.data[0]['total'] == 2

        user_one_experience = Experience.objects.create(
            created_by = Test.user_one,
            name = 'user_one_experience',
            description = 'test_description',
        )

        Activity.objects.create(
            user = Test.user_one,
            experience = user_one_experience,
            type = ActivityType.COMPLETED_EXPERIENCE,
            related_user = Test.user_two,
        )
        Activity.objects.create(
            user = Test.user_one,
            experience = user_one_experience,
            type = ActivityType.LIKED_EXPERIENCE,
            related_user = Test.user_two,
        )
        Activity.objects.create(
            user = Test.user_one,
            experience = user_one_experience,
            type = ActivityType.LIKED_EXPERIENCE,
            related_user = Test.user_three,
        )

        response = self.client.get('/activities/unseen_activity_counts/')
        sorted_response = sorted(response.data, key=lambda x: x['type'])
        assert sorted_response[0]['type'] == 200
        assert sorted_response[0]['total'] == 2
        assert sorted_response[1]['type'] == 401
        assert sorted_response[1]['total'] == 1
        assert sorted_response[2]['type'] == 500
        assert sorted_response[2]['total'] == 2

    def test_send_like_notifications_sets_has_push(self):
        experience: Experience = Experience.objects.create(
            created_by = Test.user_one,
            description = 'experience'
        )
        post : Post = Post.objects.create(
            created_by = Test.user_one,
            text = 'post',
            experience = experience)
        comment : Comment = Comment.objects.create(
            created_by = Test.user_one,
            text = 'comment')
        playlist : Playlist = Playlist.objects.create(
            created_by = Test.user_one,
            description = 'playlist')
        experience_activity : Activity = Activity.objects.create(
            user = Test.user_one,
            type = ActivityType.LIKED_EXPERIENCE,
            related_user = Test.user_two,
            experience = experience,
            is_push = True)
        post_activity : Activity = Activity.objects.create(
            user = Test.user_one,
            type = ActivityType.LIKED_POST,
            related_user = Test.user_two,
            post = post,
            is_push = True)
        comment_activity : Activity = Activity.objects.create(
            user = Test.user_one,
            type = ActivityType.LIKED_COMMENT,
            related_user = Test.user_two,
            comment = comment,
            is_push = True)
        playlist_activity : Activity = Activity.objects.create(
            user = Test.user_one,
            type = ActivityType.LIKED_PLAYLIST,
            related_user = Test.user_two,
            playlist = playlist,
            is_push = True)
        self.assertFalse(experience_activity.has_pushed)
        self.assertFalse(post_activity.has_pushed)
        self.assertFalse(comment_activity.has_pushed)
        self.assertFalse(playlist_activity.has_pushed)

        call_command('send_likes_notifications')
        experience_activity.refresh_from_db()
        post_activity.refresh_from_db()
        comment_activity.refresh_from_db()
        playlist_activity.refresh_from_db()
        self.assertTrue(experience_activity.has_pushed)
        self.assertTrue(post_activity.has_pushed)
        self.assertTrue(comment_activity.has_pushed)
        self.assertTrue(playlist_activity.has_pushed)

    def test_send_experience_notifications_sets_has_push(self):
        experience_one : Experience = Experience.objects.create(
            created_by = Test.user_one,
            description = 'Sit quietly for 3 seconds'
        )
        accept_activity : Activity = Activity.objects.create(
            user = Test.user_one,
            type = ActivityType.ACCEPTED_EXPERIENCE,
            related_user = Test.user_two,
            experience = experience_one,
            is_push = True)
        complete_activity : Activity = Activity.objects.create(
            user = Test.user_one,
            type = ActivityType.COMPLETED_EXPERIENCE,
            related_user = Test.user_two,
            experience = experience_one,
            is_push = True)
        self.assertFalse(accept_activity.has_pushed)
        self.assertFalse(complete_activity.has_pushed)

        call_command('send_experience_notifications')
        accept_activity.refresh_from_db()
        complete_activity.refresh_from_db()
        # Client wants accepts to be hidden for now
        # self.assertTrue(accept_activity.has_pushed)
        self.assertTrue(complete_activity.has_pushed)

    def test_send_playlist_notifications_sets_has_push(self):
        playlist : Playlist = Playlist.objects.create(
            created_by = Test.user_one,
            description = 'playlist')
        accept_activity : Activity = Activity.objects.create(
            user = Test.user_one,
            type = ActivityType.ACCEPTED_PLAYLIST,
            related_user = Test.user_two,
            playlist = playlist,
            is_push = True)
        self.assertFalse(accept_activity.has_pushed)

        call_command('send_playlist_accept_notifications')
        accept_activity.refresh_from_db()
        self.assertTrue(accept_activity.has_pushed)
