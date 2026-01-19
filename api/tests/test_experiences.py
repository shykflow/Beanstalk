import json
import datetime
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from freezegun import freeze_time

from api.models import (
    Activity,
    Experience,
    User,
    ExperienceAccept,
    ExperienceSave,
    ExperienceCompletion,
    Post,
    SavePersonalBucketList,
)
from api.enums import ActivityType
from api.testing_overrides import TestFiles
from . import disable_logging, SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    user_one: User
    user_two: User
    experience: Experience
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
        Test.experience = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.user_one)
        Test.token = Token.objects.create(user=Test.user_one)
        Test.token_two = Token.objects.create(user=Test.user_two)


    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')


    def test_retrieve_model(self):
        # GET valid experience
        response = self.client.get(f'/experiences/{Test.experience.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'test_experience')
        self.assertEqual(response.data['created_by']['id'], Test.user_one.id)
        self.assertEqual(response.data['created_by']['username'], Test.user_one.username)

        # GET invalid experience
        response = self.client.get('/experiences/-1/')
        self.assertEqual(response.status_code, 404)


    def test_create_model(self):
        # POST valid experience
        response = self.client.post('/experiences/', {
            'json': json.dumps({
                'name': 'test_experience_two',
                'description': 'test description',
            })
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'test_experience_two')
        self.assertEqual(response.data['created_by']['id'], Test.user_one.id)
        self.assertEqual(response.data['description'], 'test description')

    # POST invalid experience (no name)
        response = self.client.post('/experiences/', {
            'json': json.dumps({
                'description': 'test description',
            })
        })
        self.assertEqual(response.status_code, 400)


    def test_create_model_with_highlight_image(self):
        response = self.client.post('/experiences/', data={
            'highlight_image': TestFiles.get_simple_uploaded_file('jpg'),
            'json': json.dumps({
                'name': 'test_experience_two',
                'description': 'test description',
            })
        })
        self.assertEqual(response.status_code, 201)
        response = self.client.post('/experiences/', {
            'highlight_image': TestFiles.get_simple_uploaded_file('heic'),
            'json': json.dumps({
                'name': 'test_experience_three',
                'description': 'test description',
            })
        })
        self.assertEqual(response.status_code, 201)


    def test_with_website(self):
        values = [
            {"website": 'http://www.test.com', "expected": 'http://www.test.com' },
            {"website": 'https://www.test.com',"expected": 'https://www.test.com'},
            {"website": 'www.test.com',        "expected": 'www.test.com'        },
            {"website": None,                  "expected": None                  },
            {"website": '',                    "expected": None                  },
            {"website": ' ',                   "expected": None                  },
            {"website": '\n',                  "expected": None                  },
            {"website": ' \n ',                "expected": None                  },
        ]
        for i in range(len(values)):
            test_dict = values[i]
            # POST
            response = self.client.post('/experiences/', data={
                'json': json.dumps({
                    'name': f'test_website_{i}',
                    'description': 'test description',
                    'website': test_dict['website'],
                })
            })
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['website'], test_dict['expected'])
            id = response.data['id']
            # PUT
            response = self.client.put(f'/experiences/{id}/', data={
                'json': json.dumps({
                    'name': f'test_website_{i}',
                    'description': 'test description',
                    'website': test_dict['website'],
                })
            })
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertEqual(response.data['website'], test_dict['expected'])



    def test_create_also_accepts(self):
        # POST valid experience
        response = self.client.post('/experiences/', {
            'json': json.dumps({
                'name': 'test_experience_two',
                'description': 'test description',
            })
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'test_experience_two')
        self.assertTrue(ExperienceAccept.objects \
            .filter(user=Test.user_one, experience__id=response.data['id']) \
            .exists())


    def test_list_model(self):
        # GET list of experiences (should only be 1)
        response = self.client.get('/experiences/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        exp_dict = response.data['results'][0]
        self.assertEqual(exp_dict['name'], 'test_experience')
        self.assertEqual(exp_dict['created_by']['id'], Test.user_one.id)
        self.assertEqual(exp_dict['created_by']['username'], Test.user_one.username)

        # POST valid experience for user two
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.post('/experiences/', {
            'json': json.dumps({
                'name': 'test_experience_two',
                'description': 'test description',
            })
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'test_experience_two')
        self.assertEqual(response.data['created_by']['id'], Test.user_two.id)

        # GET list of experiences (should be 2 now)
        response = self.client.get('/experiences/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)

        # GET experiences filtered by created_by user_one
        response = self.client.get(f'/experiences/?created_by={Test.user_one.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        exp_dict = response.data['results'][0]
        self.assertEqual(exp_dict['name'], 'test_experience')
        self.assertEqual(exp_dict['created_by']['id'], Test.user_one.id)

        # GET experiences filtered by created_by user_two
        response = self.client.get(f'/experiences/?created_by={Test.user_two.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)
        exp_dict = response.data['results'][0]
        self.assertEqual(exp_dict['name'], 'test_experience_two')
        self.assertEqual(exp_dict['created_by']['id'], Test.user_two.id)

        # Filter with no matches should 200 but return nothing
        response = self.client.get('/experiences/?created_by=-1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertIn('next_page', response.data)
        self.assertIn('previous_page', response.data)

        # Poorly written queries will show duplicates when other users have accepted/completed experiences
        user_three = User.objects.create(
            username = 'test_user_three',
            email = 'testuserthree@email.com',
            email_verified = True)
        Test.user_one.accepted_experiences.add(Test.experience)
        Test.user_one.completed_experiences.add(Test.experience)
        user_three.accepted_experiences.add(Test.experience)
        user_three.completed_experiences.add(Test.experience)

        # Filter with accepted
        Test.user_two : User
        Test.user_two.accepted_experiences.add(Test.experience)
        response = self.client.get(f'/experiences/?accepted_by={Test.user_two.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        Test.user_two.accepted_experiences.remove(Test.experience)
        response = self.client.get(f'/experiences/?accepted_by={Test.user_two.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)


    def test_update_model(self):
         # PUT valid experience name
        response = self.client.put(f'/experiences/{Test.experience.id}/', {
            'json': json.dumps({
                'name': 'test_updated_experience',
                'description': 'new_description',
                'replace_highlight_image': False,
                'replace_video': False,
            })
        })
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data['name'], 'test_updated_experience')
        updated_experience : Experience = Experience.objects \
            .filter(id=Test.experience.id).first()
        self.assertEqual(updated_experience.name, 'test_updated_experience')
        self.assertEqual(updated_experience.description, 'new_description')

        # PUT invalid experience no name included
        response = self.client.put(f'/experiences/{Test.experience.id}/', {
            'json': json.dumps({})
        })
        self.assertEqual(response.status_code, 400)


        # PUT make sure it doesn't fail with attachments even though they are ignored
        response = self.client.put(f'/experiences/{Test.experience.id}/', {
            'json': json.dumps({
                'name': 'test_updated_experience',
                'replace_highlight_image': False,
                'replace_video': False,
                'attachments': []
            })
        })
        self.assertEqual(response.status_code, 202)

        # PUT different user attempted to change experience
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        response = self.client.put(f'/experiences/{Test.experience.id}/', {
            'json': json.dumps({
                'name': 'test_updated_experience',
                'replace_highlight_image': False,
                'replace_video': False,
            })
        })
        self.assertEqual(response.status_code, 401)



    @disable_logging
    def test_invalid_list_model(self):
        with self.assertRaises(ValueError):
            self.client.get('/experiences/?created_by=abc123')
        with self.assertRaises(ValueError):
            self.client.get('/experiences/?created_by=1.1')

        with self.assertRaises(ValueError):
            self.client.get('/experiences/?accepted_by=abc123')
        with self.assertRaises(ValueError):
            self.client.get('/experiences/?accepted_by=1.1')


    def test_mark_seen(self):
        with self.settings(SKIP_MARK_FOLLOW_FEED_SEEN=False):
            self.assertEqual(Test.user_one.seen_experiences.all().count(), 0)

            response = self.client.post(f'/experiences/{Test.experience.id}/mark_seen/')
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.data)

            self.assertEqual(Test.user_one.seen_experiences.all().count(), 1)


    def test_accept_experience(self):
        response = self.client.post(f'/experiences/{Test.experience.id}/accept/')
        assert response.status_code == 200
        accept = ExperienceAccept.objects.filter(experience=Test.experience.id).first()
        assert accept.user.id == Test.user_one.id

        response = self.client.delete(f'/experiences/{Test.experience.id}/accept/')
        assert response.status_code == 204
        accept = ExperienceAccept.objects.filter(experience=Test.experience.id).first()
        assert accept == None


    def test_save_experience(self):
        response = self.client.post(f'/experiences/{Test.experience.id}/save/')
        assert response.status_code == 200
        accept = ExperienceSave.objects.filter(experience=Test.experience.id).first()
        assert accept.user.id == Test.user_one.id

        response = self.client.delete(f'/experiences/{Test.experience.id}/save/')
        assert response.status_code == 204
        accept = ExperienceSave.objects.filter(experience=Test.experience.id).first()
        assert accept == None

    def test_save_experience_to_personal_bucket_list(self):
        response = self.client.post(f'/experiences/{Test.experience.id}/save_to_bucket_list/')
        assert response.status_code == 200
        accept = SavePersonalBucketList.objects.filter(experience=Test.experience.id).first()
        assert accept.user.id == Test.user_one.id

        response = self.client.delete(f'/experiences/{Test.experience.id}/save_to_bucket_list/')
        assert response.status_code == 204
        accept = SavePersonalBucketList.objects.filter(experience=Test.experience.id).first()
        assert accept == None



    @freeze_time("2022-12-20 10:00:00")
    def test_save_experience_with_times(self):
        start_time = '2022-12-24T00:00:00Z'
        end_time = '2022-12-25T00:00:00Z'
        response = self.client.post('/experiences/', {
            'json': json.dumps({
                'name': 'test_experience_two',
                'description': 'test description',
                'start_time': start_time,
                'end_time': end_time,
                'start_time_date_only': False,
                'end_time_date_only': False,
                'use_local_time': False
            })
        })
        self.assertEqual(response.status_code, 201)
        assert response.data['start_time'] == start_time
        assert response.data['end_time'] == end_time
        assert not response.data['start_time_date_only']
        assert not response.data['end_time_date_only']
        assert not response.data['use_local_time']

        # start time after end time
        name = 'i_should_not_exist'
        response = self.client.post('/experiences/', {
            'json': json.dumps({
                'name': name,
                'description': 'test description',
                'start_time': '2022-12-24T00:00:00.00',
                'end_time': '2022-12-23T00:00:00.00Z',
            })
        })
        self.assertEqual(response.status_code, 400)
        assert Experience.objects.filter(name=name).first() == None

        # end time in the past
        response = self.client.post('/experiences/', {
            'json': json.dumps({
                'name': name,
                'description': 'test description',
                'end_time': '2021-12-23T00:00:00.00',
            })
        })
        self.assertEqual(response.status_code, 400)
        assert Experience.objects.filter(name=name).first() == None

    def test_complete_experience(self):
        self.client.post(f'/experiences/{Test.experience.id}/accept/')
        response = self.client.post(f'/experiences/{Test.experience.id}/complete/', data={'minutes_offset': 0})
        assert response.status_code == 200
        assert ExperienceCompletion.objects.filter(experience=Test.experience.id).exists()

        # Dont complete experiences twice
        response = self.client.post(f'/experiences/{Test.experience.id}/complete/', data={'minutes_offset': 0})
        assert response.status_code == 400


        # Create post on experience completion
        experience_two: Experience = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.user_one)
        text = 'test_completion_post_text'
        ExperienceAccept.objects.create(
            experience = experience_two,
            user = Test.user_one,)
        data = {
            'post': {
                'text': text,
                'name': 'name',
            },
            'minutes_offset': 0
        }
        response = self.client.post(f'/experiences/{experience_two.id}/complete/', data=data, format='json')
        assert response.status_code == 201
        assert Post.objects.filter(text=text).exists()
        assert ExperienceCompletion.objects.filter(experience=experience_two.id).exists()


    # Reviewing without completing was enabled by turning off completion times checks.
    # @freeze_time("2022-01-20 10:00:00")
    # def test_experience_complete_time(self):
    #     self.client.post(f'/experiences/{Test.experience.id}/accept/')
    #     now = datetime.datetime.now(tz=timezone.utc)

    #     # Dont accept 1 day before start with start_time_date_only
    #     experience: Experience = Test.experience
    #     experience.start_time = now + datetime.timedelta(days=1)
    #     experience.start_time_date_only = True
    #     experience.save()
    #     response = self.client.post(f'/experiences/{Test.experience.id}/complete/', data={'minutes_offset': 0})
    #     assert response.status_code == 400

    #     # Dont accept 1 minute before start without start_time_date_only
    #     experience.start_time_date_only = False
    #     experience.start_time = now + datetime.timedelta(minutes=1)
    #     experience.save()
    #     response = self.client.post(f'/experiences/{Test.experience.id}/complete/', data={'minutes_offset': 0})
    #     assert response.status_code == 400

    #     # Dont accept 1 day after start with end_time_date_only
    #     experience.start_time = None
    #     experience.end_time = now - datetime.timedelta(days=1)
    #     experience.end_time_date_only = True
    #     experience.save()
    #     response = self.client.post(f'/experiences/{Test.experience.id}/complete/', data={'minutes_offset': 0})
    #     assert response.status_code == 400

    #     # Dont accept 1 minute after start without end_time_date_only
    #     experience.end_time = now - datetime.timedelta(minutes=1)
    #     experience.end_time_date_only = False
    #     experience.save()
    #     response = self.client.post(f'/experiences/{Test.experience.id}/complete/', data={'minutes_offset': 0})
    #     assert response.status_code == 400

    #     # Dont allow offset > |24| hours
    #     experience.end_time = None
    #     experience.save()
    #     response = self.client.post(f'/experiences/{Test.experience.id}/complete/', data={'minutes_offset': 1441})
    #     assert response.status_code == 400
    #     response = self.client.post(f'/experiences/{Test.experience.id}/complete/', data={'minutes_offset': -1441})
    #     assert response.status_code == 400

    #     # Dont accept if the offset falls 1 minute outside of experience start
    #     experience.start_time = now
    #     experience.start_time_date_only = False
    #     experience.save()
    #     response = self.client.post(f'/experiences/{Test.experience.id}/complete/', data={'minutes_offset': -1})
    #     assert response.status_code == 400

    #     # Dont accept if the offset falls 1 minute outside of experience end
    #     experience.start_time = None
    #     experience.end_time = now
    #     experience.end_time_date_only = False
    #     experience.save()
    #     response = self.client.post(f'/experiences/{Test.experience.id}/complete/', data={'minutes_offset': 1})
    #     assert response.status_code == 400

    #     # Accept experience within tight bounds
    #     experience.start_time = now - datetime.timedelta(minutes=1)
    #     experience.end_time = now + datetime.timedelta(minutes=1)
    #     experience.end_time_date_only = False
    #     experience.save()
    #     response = self.client.post(f'/experiences/{Test.experience.id}/complete/', data={'minutes_offset': 0})
    #     assert response.status_code == 200
    #     completion = ExperienceCompletion.objects.filter(experience=experience.id)
    #     assert completion.exists()

    #     # Accept experience within 1 day bounds with date_only
    #     # Start day should act inclusively and end day should be exclusively
    #     completion.delete()
    #     experience.start_time = now
    #     experience.start_time_date_only = True
    #     experience.end_time = now + datetime.timedelta(days=1)
    #     experience.end_time_date_only = True
    #     experience.save()
    #     response = self.client.post(f'/experiences/{Test.experience.id}/complete/', data={'minutes_offset': 0})
    #     assert response.status_code == 200
    #     completion = ExperienceCompletion.objects.filter(experience=experience.id)
    #     assert completion.exists()


    def test_experience_accept_generates_activity(self):
        experience_two = Experience.objects.create(
            name = 'test_experience_two',
            created_by = Test.user_two)
        with self.assertRaises(Activity.DoesNotExist):
            # Should raise exception since no Activity exists in the database
            generated_activity: Activity = Activity.objects.get(experience=experience_two, type=ActivityType.ACCEPTED_EXPERIENCE)

        self.client.post(f'/experiences/{experience_two.id}/accept/')

        # Should not raise exception since now a matching Activity exists
        generated_activity: Activity = Activity.objects.get(experience=experience_two, type=ActivityType.ACCEPTED_EXPERIENCE)
        self.assertEqual(generated_activity.user, Test.user_two)
        self.assertEqual(generated_activity.related_user, Test.user_one)
        self.assertEqual(generated_activity.type, 400)
        self.assertEqual(generated_activity.experience.id, experience_two.id)


    def test_accepting_own_experience_does_not_generates_activity(self):
        experience: Experience = Experience.objects.create(
            name = 'test_experience_two',
            created_by = Test.user_one)
        self.client.post(f'/experiences/{experience.id}/accept/')
        self.assertFalse(Activity.objects.filter(
            experience=experience, type=ActivityType.ACCEPTED_EXPERIENCE).exists())


    def test_experience_complete_generates_activity(self):
        experience_two = Experience.objects.create(
            name = 'test_experience_two',
            created_by = Test.user_two)
        Test.user_one.accepted_experiences.add(experience_two)
        self.assertFalse(Activity.objects.filter(
            user=Test.user_two,
            experience=experience_two,
            type=ActivityType.COMPLETED_EXPERIENCE,
            related_user=Test.user_one).exists())
        self.client.post(f'/experiences/{experience_two.id}/complete/', data={'minutes_offset': 0})
        self.assertTrue(Activity.objects.filter(
            user=Test.user_two,
            experience=experience_two,
            type=ActivityType.COMPLETED_EXPERIENCE,
            related_user=Test.user_one).exists())


    def test_completing_own_experience_does_not_generates_activity(self):
        experience = Experience.objects.create(
            name = 'test_experience_two',
            created_by = Test.user_one)
        self.client.post(f'/experiences/{experience.id}/complete/')
        self.assertFalse(Activity.objects.filter(
            experience=experience, type=ActivityType.COMPLETED_EXPERIENCE).exists())


    @freeze_time("2022-12-20 10:00:00")
    def test_updated_experience_by_setting_nulls(self):
        response = self.client.post('/experiences/', {
            'highlight_image': TestFiles.get_simple_uploaded_file('jpg'),
            'highlight_image_thumbnail': TestFiles.get_simple_uploaded_file('jpg'),
            'video': TestFiles.get_simple_uploaded_file('mp4'),
            'json': json.dumps({
                'name': 'name',
                'description': 'test description',
                'start_time': '2022-11-23T00:00:00.00Z',
                'end_time': '2022-12-23T00:00:00.00Z',
                'latitude': 50,
                'longitude': 50,
            })
        })
        self.assertEqual(response.status_code, 201)

        # Remove start/end times, description, lat/long, highlight_image, thumbnail, and video
        id = response.data['id']
        response = self.client.put(f'/experiences/{id}/', data={
            'json': json.dumps({
                'name': 'name',
                'description': None,
                'end_time': None,
                'start_time': None,
                'latitude': None,
                'longitude': None,
                'replace_highlight_image_thumbnail': True,
                'replace_highlight_image': True,
                'replace_video': True,
            })
        })
        self.assertEqual(response.status_code, 202)
        exp: Experience = Experience.objects.filter(id=id).first()
        self.assertIsNone(exp.description)
        self.assertIsNone(exp.end_time)
        self.assertIsNone(exp.start_time)
        self.assertIsNone(exp.latitude)
        self.assertIsNone(exp.longitude)
        # images/videos will still be type ImageFieldFile/FieldFile, but their effective value is None
        # They raise a value error if None, since a ImageFieldFile: None has no url
        with self.assertRaises(ValueError):
            exp.highlight_image.url
        with self.assertRaises(ValueError):
            exp.highlight_image_thumbnail.url
        with self.assertRaises(ValueError):
            exp.video.url


    def test_retrieve_accepted_users(self):
        ExperienceAccept.objects.create(
            experience = Test.experience,
            user = Test.user_one)
        ExperienceAccept.objects.create(
            experience = Test.experience,
            user = Test.user_two)
        response = self.client.get(f'/experiences/{Test.experience.id}/accepted_users/')
        self.assertEqual(response.status_code, 200)
        # Should be in reverse order of the accept's creation
        self.assertEqual(response.data['results'][0]['model'], 'User')
        self.assertEqual(response.data['results'][0]['id'], Test.user_two.id)
        self.assertEqual(response.data['results'][1]['id'], Test.user_one.id)


    def test_retrieve_experience_posts(self):
        post_one = Post.objects.create(
            created_by=Test.user_one,
            experience=Test.experience,
            name='test post one',
            text='test post one text'
        )
        post_two = Post.objects.create(
            created_by=Test.user_two,
            experience=Test.experience,
            name='test post two',
            text='test post two text'
        )

        response = self.client.get(f'/experiences/{Test.experience.id}/posts/')
        self.assertEqual(response.status_code, 200)
        # Should be in reverse order of the post's creation
        self.assertEqual(response.data['results'][0]['model'], 'Post')
        self.assertEqual(response.data['results'][0]['id'], post_two.id)
        self.assertEqual(response.data['results'][1]['id'], post_one.id)



    def test_experience_has_correct_total_accepts(self):
        other_user = User.objects.create(
            username='other',
            email='other@email.com',
            email_verified=True)
        exp: Experience = Experience.objects.create(
            name='asdf',
            created_by=Test.user_one)
        endpoint = f'/experiences/{exp.id}/?details=true'

        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_accepts'], 0)

        Test.user_one.accepted_experiences.add(exp)
        exp.calc_total_accepts(set_and_save=True)
        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_accepts'], 1)

        other_user.accepted_experiences.add(exp)
        exp.calc_total_accepts(set_and_save=True)
        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_accepts'], 2)


    def test_experience_has_correct_total_completes(self):
        other_user = User.objects.create(
            username='other',
            email='other@email.com',
            email_verified=True)
        exp: Experience = Experience.objects.create(
            name='asdf',
            created_by=Test.user_one)
        endpoint = f'/experiences/{exp.id}/?details=true'

        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_completes'], 0)

        Test.user_one.completed_experiences.add(exp)
        exp.calc_total_completes(set_and_save=True)
        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_completes'], 1)

        other_user.completed_experiences.add(exp)
        exp.calc_total_completes(set_and_save=True)
        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_completes'], 2)


    def test_experience_has_correct_total_likes(self):
        other_user = User.objects.create(
            username='other',
            email='other@email.com',
            email_verified=True)
        exp: Experience = Experience.objects.create(
            name='asdf',
            created_by=Test.user_one)
        endpoint = f'/experiences/{exp.id}/?details=true'

        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_likes'], 0)

        exp.likes.add(Test.user_one)
        exp.calc_total_likes(set_and_save=True)
        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_likes'], 1)

        exp.likes.add(other_user)
        exp.calc_total_likes(set_and_save=True)
        response = self.client.get(endpoint)
        exp_dict: dict[str, any] = response.data
        self.assertEqual(exp_dict['total_likes'], 2)
