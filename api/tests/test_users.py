import pytz
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from requests.exceptions import ConnectionError
from rest_framework.authtoken.models import Token
from os import environ

from api.models import (
    Playlist,
    PlaylistCompletion,
    Experience,
    ExperienceCompletion,
    User,
)
from . import SilenceableAPITestCase
from lf_service.util import LifeFrameUtilService

# Notes on the difference between setUpTestData() and setUp()
# https://stackoverflow.com/questions/29428894/django-setuptestdata-vs-setup

class Test(SilenceableAPITestCase):
    should_fake_life_frame_id: bool
    email_backend: str
    verified_user: User
    unverified_user: User
    verified_token: Token
    unverified_token: Token

    # Ran before all tests only once.
    def setUpTestData():
        try:
            response = LifeFrameUtilService().healthcheck()
            if response.status_code != 200:
                raise ConnectionError
            Test.should_fake_life_frame_id = False
        except ConnectionError:
            Test.should_fake_life_frame_id = True
        Test.email_backend = environ.get('EMAIL_BACKEND')
        Test.verified_user = User(
            username = 'test_user_verified',
            email = 'testverified_user@email.com',
            email_verified = True,
        )
        Test.verified_user.set_password('Test1234$')
        now = timezone.datetime.now(tz=pytz.timezone("UTC"))
        Test.unverified_user = User(
            username = 'test_user_unverified',
            email = 'testunverified_user@email.com',
            email_verified = False,
            code_requested_at = now,
            verification_code = '12345678',
        )
        if Test.should_fake_life_frame_id:
            Test.verified_user.life_frame_id = 'fake'
            Test.unverified_user.life_frame_id = 'fake'
        Test.verified_user.save()
        Test.unverified_user.save()
        Test.verified_token = Token.objects.create(user=Test.verified_user)
        Test.unverified_token = Token.objects.create(user=Test.unverified_user)


    # Ran before each test.
    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.unverified_token}')


    def test_retrieve_model(self):
        # Unverified user credentials should 403
        response = self.client.get(f'/users/{Test.unverified_user.id}/')
        self.assertEqual(response.status_code, 403)

        # Verified user credentials should 200
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')
        response = self.client.get(f'/users/{Test.unverified_user.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'test_user_unverified')
        self.assertFalse(response.data['email_verified'])
        self.assertIsNone(response.data.get('follows_viewer'))
        self.assertIsNone(response.data.get('followed_by_viewer'))
        self.assertIsNone(response.data.get('follower_count'))
        self.assertIsNone(response.data.get('sampled_common_outgoing_follow_users'))

        # Sending include_relationship_data should include follow data
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')
        response = self.client.get(f'/users/{Test.unverified_user.id}/?include_relationship_data=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'test_user_unverified')
        self.assertFalse(response.data['email_verified'])
        self.assertFalse(response.data['follows_viewer'])
        self.assertFalse(response.data['followed_by_viewer'])
        self.assertEqual(response.data['follower_count'], 0)
        self.assertEqual(response.data['sampled_common_outgoing_follow_users'], [])

        # Sending include_completion_counts should include experience and playlist completion counts
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')
        response = self.client.get(f'/users/{Test.verified_user.id}/?include_completion_counts=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['num_experiences_completed'], 0)
        self.assertEqual(response.data['num_playlists_completed'], 0)
        experience: Experience = Experience.objects.create(
            name = 'test_experience',
            created_by = Test.verified_user)
        ExperienceCompletion.objects.create(
            experience = experience,
            user = Test.verified_user)
        playlist: Playlist = Playlist.objects.create(
            name = 'test_playlist',
            created_by = Test.verified_user)
        PlaylistCompletion.objects.create(
            playlist = playlist,
            user = Test.verified_user)
        response = self.client.get(f'/users/{Test.verified_user.id}/?include_completion_counts=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['num_experiences_completed'], 1)
        self.assertEqual(response.data['num_playlists_completed'], 1)

        # GET nonexistent user should 404
        response = self.client.get('/users/-1/')
        self.assertEqual(response.status_code, 404)


    def test_list_model(self):
        # Unverified user credentials should 403
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, 403)

        # Verified user credentials should 200
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')
        response = self.client.get(f'/users/?users={Test.unverified_user.id},{Test.verified_user.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['username'], 'test_user_verified')
        self.assertTrue(response.data[0]['email_verified'])
        self.assertIsNone(response.data[0].get('follows_viewer'))
        self.assertIsNone(response.data[0].get('followed_by_viewer'))
        self.assertIsNone(response.data[0].get('follower_count'))
        self.assertEqual(response.data[1]['username'], 'test_user_unverified')
        self.assertFalse(response.data[1]['email_verified'])
        self.assertIsNone(response.data[1].get('follows_viewer'))
        self.assertIsNone(response.data[1].get('followed_by_viewer'))
        self.assertIsNone(response.data[1].get('follower_count'))

        # Sending include_relationship_data should include follow data
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')
        response = self.client.get(f'/users/?users={Test.unverified_user.id}&include_relationship_data=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'test_user_unverified')
        self.assertFalse(response.data[0]['email_verified'])
        self.assertFalse(response.data[0]['follows_viewer'])
        self.assertFalse(response.data[0]['followed_by_viewer'])
        self.assertEqual(response.data[0]['follower_count'], 0)

        # Any one of the users found should 200 even if others were not found
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')
        response = self.client.get(f'/users/?users=-1,{Test.unverified_user.id},-2,-3')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], 'test_user_unverified')
        self.assertFalse(response.data[0]['email_verified'])
        self.assertIsNone(response.data[0].get('follows_viewer'))
        self.assertIsNone(response.data[0].get('followed_by_viewer'))
        self.assertIsNone(response.data[0].get('follower_count'))

        # Passing in no user IDs should 404
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, 404)

        # Passing in only nonexistent user IDs should 404
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')
        response = self.client.get('/users/?users=-1,-2,-3')
        self.assertEqual(response.status_code, 404)


    def test_signup_invalid(self):
        username = 'test_user'
        email = 'testuser@email.com'
        response = self.client.post('/users/sign_up/',
            {},
            format='json')
        assert response.status_code == 400

        response = self.client.post('/users/sign_up/', {
                'username': username,
            },
            format='json')
        assert response.status_code == 400

        response = self.client.post('/users/sign_up/', {
                'username': username,
                'email': email,
            },
            format='json')
        assert response.status_code == 400


    def test_signup(self):
        username = 'test_user'
        email = 'testuser@email.com'
        password = 'Test1234$'
        # Create the user
        response = self.client.post('/users/sign_up/', {
                'username': username,
                'email': email,
                'password': password,
            },
            format='json')
        assert response.status_code == 200


        # Create the user again, should replace the existing user
        # because the user has not verified their email,
        # This time with 'profile_picture': None, should still work
        response = self.client.post('/users/sign_up/', {
                'username': username,
                'email': email,
                'password': password,
                'profile_picture': None,
            },
            format='json')
        assert response.status_code == 200
        token = response.data.get('token')
        assert token is not None
        # Set the client's credentials for the newly-created user
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Get user from token
        response = self.client.get('/users/user_from_token/')
        assert response.status_code == 200
        user_data = response.data
        assert 'id' in user_data.keys()
        assert 'username' in user_data.keys()
        assert 'email' in user_data.keys()
        assert 'email_verified' in user_data.keys()
        assert 'profile_picture' in user_data.keys()
        assert 'profile_picture_thumbnail' in user_data.keys()
        id = user_data.get('id')
        assert id is not None

        # Verify email from user that was just created
        user: User = User.objects.filter(id=id).first()
        assert user is not None
        assert user.verification_code is not None
        if Test.should_fake_life_frame_id:
            user.life_frame_id = 'fake'
            user.save()
        response = self.client.post('/users/verify_email/', {
            'verification_code': user.verification_code,
        })
        assert response.status_code == 200


    def test_signup_does_not_delete_verified_user(self):
        # Valid user that should not be deleted
        user = User.objects.create(
            username='valid_user_dont_delete_me',
            email='email_valid_user@emailservice.corn',
            email_verified=True)

        # Create the user
        response = self.client.post('/users/sign_up/', {
                'username': 'valid_user_dont_delete_me',
                'email': 'unique_email@emailservice.corn',
                'password': 'Test1234$',
            },
            format='json')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(id=user.id).exists())


    def test_resend_verification_email(self):
        # Since code_requested_at was set to now, this will time out and 400
        response = self.client.post('/users/resend_verification_email/')
        self.assertEqual(response.status_code, 400)

        # Already-verified user will 400
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')
        response = self.client.post('/users/resend_verification_email/')
        self.assertEqual(response.status_code, 400)

        # Test a successful request only if the email_backend is console
        if Test.email_backend != 'console':
            return
        # Create a user who requested a code in the past
        past_user: User = User.objects.create(
            username = 'user_whose_code_requested_at_is_in_the_past',
            email = 'fake@email.com',
            email_verified = False,
            code_requested_at=timezone.datetime(2022, 1, 1, tzinfo=pytz.UTC),
        )
        u_token: Token = Token.objects.create(user=past_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {u_token}')
        self.assertIsNone(past_user.verification_code)
        old_code_requested_at = past_user.code_requested_at

        response = self.client.post('/users/resend_verification_email/')
        self.assertEqual(response.status_code, 200)
        past_user.refresh_from_db()
        self.assertIsNotNone(past_user.verification_code)
        self.assertNotEqual(old_code_requested_at, past_user.code_requested_at)


    def test_verify_email_invalid(self):
        assert Test.unverified_user is not None
        assert Test.unverified_user.verification_code is not None
        assert Test.unverified_token is not None
        response = self.client.post('/users/verify_email/', {
            'verification_code': None,
        }, format='json')
        assert response.status_code == 400
        response = self.client.post('/users/verify_email/', {
            'verification_code': 'BAD_CODE',
        })
        assert response.status_code == 400


    def test_verify_email(self):
        assert Test.unverified_user is not None
        assert Test.unverified_user.verification_code is not None
        assert Test.unverified_token is not None
        response = self.client.post('/users/verify_email/', {
            'verification_code': Test.unverified_user.verification_code,
        })
        assert response.status_code == 200

        # Try to verify their email again,
        # should fail because they are already verified
        response = self.client.post('/users/verify_email/', {
            'verification_code': Test.unverified_user.verification_code,
        })
        assert response.status_code == 400


    def test_verify_email_for_password_change(self):
        # Email that does not belong to a user should 400
        response = self.client.post('/users/verify_email_for_password_change/', {
            'email': 'abc123@email.com',
            'verification_code': '55555555',
        }, format='json')
        self.assertEqual(response.status_code, 400)

        # User without verification code should 400
        no_verification_code_user: User = User.objects.create(
            username = 'user_who_does_not_have_verification_code',
            email = 'fake@email.com',
            email_verified = False,
            code_requested_at=timezone.datetime(2022, 1, 1, tzinfo=pytz.UTC),
        )
        no_verification_code_token: Token = Token.objects.create(user=no_verification_code_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {no_verification_code_token}')
        response = self.client.post('/users/verify_email_for_password_change/', {
            'email': no_verification_code_user.email,
            'verification_code': '55555555',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('verification_code', response.data)
        self.assertEqual(response.data['verification_code'][0], 'Verification code not found.')

        # Non-matching verification codes should 400
        response = self.client.post('/users/verify_email_for_password_change/', {
            'email': 'testunverified_user@email.com',
            'verification_code': '55555555',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('verification_code', response.data)
        self.assertEqual(response.data['verification_code'][0], 'Verification code does not match.')

        # Matching verification codes should 200
        response = self.client.post('/users/verify_email_for_password_change/', {
            'email': 'testunverified_user@email.com',
            'verification_code': '12345678',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)


    def test_change_password(self):
        # No password sent should 400
        response = self.client.post(f'/users/{Test.unverified_user.id}/change_password/', {
            'email': 'testunverified_user@email.com',
        }, format='json')
        self.assertEqual(response.status_code, 400)

        # No email sent should 400
        response = self.client.post(f'/users/{Test.unverified_user.id}/change_password/', {
            'password': 'opensesame',
        }, format='json')
        self.assertEqual(response.status_code, 400)

        # Nonexistent user ID should 401
        response = self.client.post(f'/users/-1/change_password/', {
            'email': 'nonexistent_user@email.com',
            'password': 'opensesame',
        }, format='json')
        self.assertEqual(response.status_code, 401)

        # Non-matching email should 401
        response = self.client.post(f'/users/{Test.unverified_user.id}/change_password/', {
            'email': 'nonexistent_user@email.com',
            'password': 'opensesame',
        }, format='json')
        self.assertEqual(response.status_code, 401)

        # Valid data should 200 and change the password
        previous_password_hash = Test.unverified_user.password
        response = self.client.post(f'/users/{Test.unverified_user.id}/change_password/', {
            'email': 'testunverified_user@email.com',
            'password': 'opensesame',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        Test.unverified_user.refresh_from_db()
        self.assertNotEqual(previous_password_hash, Test.unverified_user.password)


    def test_get_password_reset_email(self):
        # No email sent should 400
        response = self.client.post('/users/get_password_reset_email/')
        self.assertEqual(response.status_code, 400)

        # Nonexistent email should 400
        response = self.client.post('/users/get_password_reset_email/', {
            'email': 'nonexistent_user@email.com',
        }, format='json')
        self.assertEqual(response.status_code, 400)

        # Requesting another email should 400
        response = self.client.post('/users/get_password_reset_email/', {
            'email': 'testunverified_user@email.com',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('verification_code', response.data)
        self.assertIn('resend_email_timeout', response.data)

        # Test a successful request only if the email_backend is console
        if Test.email_backend != 'console':
            return
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')
        # Valid request should 200 and set the verification_code and code_requested_at
        self.assertIsNone(Test.verified_user.code_requested_at)
        self.assertIsNone(Test.verified_user.verification_code)
        response = self.client.post('/users/get_password_reset_email/', {
            'email': 'testverified_user@email.com',
        }, format='json')
        Test.verified_user.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(Test.verified_user.code_requested_at)
        self.assertIsNotNone(Test.verified_user.verification_code)


    def test_login_invalid(self):
        password = 'Test1234$'
        response = self.client.post('/users/login/', {
            'identifier': 'WRONG_USERNAME',
            'password': 'WRONG_PASSWORD',
        }, format='json')
        assert response.status_code == 400

        response = self.client.post('/users/login/', {
            'identifier': 'WRONG_USERNAME',
            'password': password,
        }, format='json')
        assert response.status_code == 400

        response = self.client.post('/users/login/', {
            'identifier': Test.verified_user.username,
            'password': 'WRONG_PASSWORD',
        }, format='json')
        assert response.status_code == 400


    def test_login_username(self):
        response = self.client.post('/users/login/', {
            'identifier': Test.verified_user.username,
            'password': 'Test1234$',
        }, format='json')
        assert response.status_code == 200
        data = response.data
        assert data.get('token') is not None
        user_data = data.get('user')
        assert user_data is not None
        assert 'id' in user_data.keys()
        assert 'username' in user_data.keys()
        assert 'email' in user_data.keys()
        assert 'email_verified' in user_data.keys()
        assert 'profile_picture' in user_data.keys()
        assert 'profile_picture_thumbnail' in user_data.keys()
        assert user_data.get('username') == Test.verified_user.username
        assert user_data.get('email') == Test.verified_user.email

        # Case insensitive username
        response = self.client.post('/users/login/', {
            'identifier': Test.verified_user.username.upper(),
            'password': 'Test1234$',
        }, format='json')
        assert response.status_code == 200
        data = response.data
        assert data.get('token') is not None


    def test_login_email(self):
        response = self.client.post('/users/login/', {
            'identifier': Test.verified_user.email,
            'password': 'Test1234$',
        }, format='json')
        assert response.status_code == 200
        data = response.data
        assert data.get('token') is not None
        user_data = data.get('user')
        assert user_data is not None
        assert 'id' in user_data.keys()
        assert 'username' in user_data.keys()
        assert 'email' in user_data.keys()
        assert 'email_verified' in user_data.keys()
        assert 'profile_picture' in user_data.keys()
        assert 'profile_picture_thumbnail' in user_data.keys()
        assert user_data.get('username') == Test.verified_user.username
        assert user_data.get('email') == Test.verified_user.email

        # Case insensitive email
        response = self.client.post('/users/login/', {
            'identifier': Test.verified_user.email.upper(),
            'password': 'Test1234$',
        }, format='json')
        assert response.status_code == 200
        data = response.data
        assert data.get('token') is not None


    def test_update_profile_picture(self):
        response = None
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')
        with open(f'{str(settings.BASE_DIR)}/api/static/test.jpg', 'rb') as testImage:
            response = self.client.post(f'/users/set_profile_picture/',
                {'profile_picture': testImage},
                format='multipart')
        assert response.status_code == 200
        Test.verified_user.refresh_from_db()
        assert bool(Test.verified_user.profile_picture)
        assert bool(Test.verified_user.profile_picture_thumbnail)

        response = self.client.post(f'/users/set_profile_picture/',
            {'profile_picture': None},
            format='json')
        assert response.status_code == 200
        Test.verified_user.refresh_from_db()
        assert not bool(Test.verified_user.profile_picture)
        assert not bool(Test.verified_user.profile_picture_thumbnail)


    def test_search(self):
        user_2: User = User.objects.create(
            username = 'user_2',
            email = 'user_2@email.com',
            email_verified = True,
        )
        # Unverified user credentials should 403
        response = self.client.get('/users/search/?q=user')
        self.assertEqual(response.status_code, 403)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')

        # Extremely long keywords_string should 400
        long_query: str = 'a' * 401
        response = self.client.get(f'/users/search/?q={long_query}')
        self.assertEqual(response.status_code, 400)

        # Just long enough keywords_string should 200
        long_query = long_query[1:]
        response = self.client.get(f'/users/search/?q={long_query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([], response.data)

        # Valid search should 200 and return the specified user(s)
        response = self.client.get(f'/users/search/?q={user_2.username}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], user_2.username)

        response = self.client.get('/users/search/?q=user')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        expected_answers = ['test_user_verified', user_2.username]
        self.assertIn(response.data[0]['username'], expected_answers)
        expected_answers.remove(response.data[0]['username'])
        self.assertIn(response.data[1]['username'], expected_answers)

        # Sending ignore_self should exclude this user
        response = self.client.get('/users/search/?q=user&ignore_self=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['username'], user_2.username)
        response = self.client.get('/users/search/?q=user_verified&ignore_self=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([], response.data)

        # Search should filter out unverified users
        response = self.client.get(f'/users/search/?q={Test.unverified_user.username}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)


    def test_user_update(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.verified_token}')
        user_2: User = User.objects.create(
            username = 'user_2',
            email = 'user_2@email.com',
            email_verified = True,
        )

        user_properties = {
            "id": self.verified_user.id,
            "name": "name",
            "username": "username",
            "tagline": "I'm a tagline!",
            "bio": "Hi, this is my bio!",
            "website": "https://thebeanstalkapp.com/",
            "birthdate": datetime(1990, 1, 1),
            "experience_visibility": 1,
            "badge_visibility": 1,
            "activity_push_pref": False,
            "like_push_pref": False,
            "mention_push_pref": False,
            "comment_push_pref": False,
            "follow_push_pref": False,
            "accept_complete_push_pref": False,
        }

        # Update user
        response = self.client.put(f'/users/{Test.verified_user.id}/', user_properties, format='json')
        self.assertEqual(response.status_code, 200)
        updated_user = User.objects.filter(id=Test.verified_user.id).first()
        self.assertEqual(updated_user.name, user_properties['name'])
        self.assertEqual(updated_user.username, user_properties['username'])
        self.assertEqual(updated_user.tagline, user_properties['tagline'])
        self.assertEqual(updated_user.bio, user_properties['bio'])
        self.assertEqual(updated_user.website, user_properties['website'])
        self.assertEqual(updated_user.badge_visibility, user_properties['badge_visibility'])
        self.assertEqual(updated_user.experience_visibility, user_properties['experience_visibility'])
        self.assertEqual(updated_user.like_push_pref, user_properties['like_push_pref'])
        self.assertEqual(updated_user.mention_push_pref, user_properties['mention_push_pref'])
        self.assertEqual(updated_user.comment_push_pref, user_properties['comment_push_pref'])
        self.assertEqual(updated_user.follow_push_pref, user_properties['follow_push_pref'])
        self.assertEqual(updated_user.accept_complete_push_pref, user_properties['accept_complete_push_pref'])


    def test_invalid_user_update(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.verified_token}')
        user_2: User = User.objects.create(
            username = 'user_2',
            email = 'user_2@email.com',
            email_verified = True,
        )

        user_properties = {
            "name": "name",
            "username": "username",
            "tagline": "I'm a tagline!",
            "bio": "Hi, this is my bio!",
            "website": "https://thebeanstalkapp.com/",
            "birthdate": datetime(1990, 1, 1),
            "experience_visibility": 1,
            "badge_visibility": 1,
            "activity_push_pref": False,
            "like_push_pref": False,
            "mention_push_pref": False,
            "comment_push_pref": False,
            "follow_push_pref": False,
            "accept_complete_push_pref": False,
        }

        # Trying to alter another user
        response = self.client.put(
            f'/users/{user_2.id}/',
            user_properties,
            format='json')
        self.assertEqual(response.status_code, 403)

        # Below the age of 13
        user_properties_below_13 = user_properties.copy()
        user_properties_below_13["birthdate"] = datetime(2020, 1, 1)
        response = self.client.put(
            f'/users/{Test.verified_user.id}/',
            user_properties_below_13,
            format='json')
        self.assertEqual(response.status_code, 400)

        # Username taken
        user_properties_username_taken = user_properties.copy()
        user_properties_username_taken["username"] = user_2.username
        response = self.client.put(
            f'/users/{Test.verified_user.id}/',
            user_properties_username_taken,
            format='json')
        self.assertEqual(response.status_code, 400)

