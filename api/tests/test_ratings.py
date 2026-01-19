from rest_framework.authtoken.models import Token

from api.models import Playlist, Experience, User
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    user_one: User
    user_two: User
    user_three: User
    user_other: User
    experience: Experience
    playlist: Playlist
    token_one: Token
    token_two: Token
    token_three: Token

    # Ran before all tests only once.
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
        Test.user_other = User.objects.create(
            username = 'test_user_other',
            email = 'testuserfour@email.com',
            email_verified = True,
        )
        Test.experience = Experience.objects.create(
            created_by = Test.user_other,
            name = 'test_experience',
            description = 'test_description',
        )
        Test.playlist = Playlist.objects.create(
            created_by = Test.user_one,
            name = 'test_playlist',
        )
        Test.token_one = Token.objects.create(user=Test.user_one)
        Test.token_two = Token.objects.create(user=Test.user_two)
        Test.token_three = Token.objects.create(user=Test.user_three)


    # Ran before each test.
    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_one}')


    def test_playlist_star_rating_invalid_requests(self):
        # Nonexistent Playlist tests
        response = self.client.put('/playlists/-1/star_rating/', {'rating': 5}, format='json')
        self.assertEqual(response.status_code, 404)

        # PUT a star rating with no body
        response = self.client.put(f'/playlists/{Test.playlist.id}/star_rating/')
        self.assertEqual(response.status_code, 400)

        # PUT a star rating with no rating
        response = self.client.put(f'/playlists/{Test.playlist.id}/star_rating/', {}, format='json')
        self.assertEqual(response.status_code, 400)

        # PUT a star rating with invalid data (incorrect data type float)
        response = self.client.put(f'/playlists/{Test.playlist.id}/star_rating/', {'rating': 1.3}, format='json')
        self.assertEqual(response.status_code, 400)

        # Invalid method for endpoint
        response = self.client.patch(f'/playlists/{Test.playlist.id}/star_rating/', {'rating': 2}, format='json')
        self.assertEqual(response.status_code, 405)


    def test_playlist_cost_rating_invalid_requests(self):
        # Nonexistent Playlist tests
        response = self.client.put('/playlists/-1/cost_rating/', {'rating': 5}, format='json')
        self.assertEqual(response.status_code, 404)

        # PUT a cost rating with no body
        response = self.client.put(f'/playlists/{Test.playlist.id}/cost_rating/')
        self.assertEqual(response.status_code, 400)

        # PUT a cost rating with no rating
        response = self.client.put(f'/playlists/{Test.playlist.id}/cost_rating/', {}, format='json')
        self.assertEqual(response.status_code, 400)

        # PUT a cost rating with invalid data (incorrect data type float)
        response = self.client.put(f'/playlists/{Test.playlist.id}/cost_rating/', {'rating': 1.3}, format='json')
        self.assertEqual(response.status_code, 400)

        # Invalid method for endpoint
        response = self.client.patch(f'/playlists/{Test.playlist.id}/cost_rating/', {'rating': 2}, format='json')
        self.assertEqual(response.status_code, 405)


    def test_playlist_star_rating_create_update(self):
        # PUT (create) star rating
        response = self.client.put(f'/playlists/{Test.playlist.id}/star_rating/', {'rating': 1}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('rating', response.data)
        self.assertEqual(response.data['rating'], 1)

        response = self.client.get(f'/playlists/{Test.playlist.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_star_rating'], 1)

        # PUT (update) star rating
        response = self.client.put(f'/playlists/{Test.playlist.id}/star_rating/', {'rating': 2}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('rating', response.data)
        self.assertEqual(response.data['rating'], 2)

        response = self.client.get(f'/playlists/{Test.playlist.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_star_rating'], 2)


    def test_playlist_cost_rating_create_update(self):
        # PUT (create) cost rating
        response = self.client.put(f'/playlists/{Test.playlist.id}/cost_rating/', {'rating': 1}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('rating', response.data)
        self.assertEqual(response.data['rating'], 1)

        response = self.client.get(f'/playlists/{Test.playlist.id}/?details=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_cost_rating'], 1)

        # PUT (update) cost rating
        response = self.client.put(f'/playlists/{Test.playlist.id}/cost_rating/', {'rating': 3}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('rating', response.data)
        self.assertEqual(response.data['rating'], 3)

        response = self.client.get(f'/playlists/{Test.playlist.id}/?details=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_cost_rating'], 3)


    def test_experience_star_rating_invalid_requests(self):
        # Nonexistent Experience tests
        response = self.client.put('/experiences/-1/star_rating/', {'rating': 1}, format='json')
        self.assertEqual(response.status_code, 404)

        # PUT a star rating with no body
        response = self.client.put(f'/experiences/{Test.experience.id}/star_rating/')
        self.assertEqual(response.status_code, 400)

        # PUT a star rating with no rating
        response = self.client.put(f'/experiences/{Test.experience.id}/star_rating/', {}, format='json')
        self.assertEqual(response.status_code, 400)

        # PUT a star rating with invalid data (incorrect data type float)
        response = self.client.put(f'/experiences/{Test.experience.id}/star_rating/', {'rating': 2.8}, format='json')
        self.assertEqual(response.status_code, 400)

        # Invalid method for endpoint
        response = self.client.patch(f'/experiences/{Test.experience.id}/star_rating/', {'rating': 2}, format='json')
        self.assertEqual(response.status_code, 405)


    def test_experience_cost_rating_invalid_requests(self):
        # Nonexistent Experience tests
        response = self.client.put('/experiences/-1/cost_rating/', {'rating': 1}, format='json')
        self.assertEqual(response.status_code, 404)

        # PUT a cost rating with no body
        response = self.client.put(f'/experiences/{Test.experience.id}/cost_rating/')
        self.assertEqual(response.status_code, 400)

        # PUT a cost rating with no rating
        response = self.client.put(f'/experiences/{Test.experience.id}/cost_rating/', {}, format='json')
        self.assertEqual(response.status_code, 400)

        # PUT a cost rating with invalid data (incorrect data type float)
        response = self.client.put(f'/experiences/{Test.experience.id}/cost_rating/', {'rating': 2.8}, format='json')
        self.assertEqual(response.status_code, 400)

        # Invalid method for endpoint
        response = self.client.patch(f'/experiences/{Test.experience.id}/cost_rating/', {'rating': 2}, format='json')
        self.assertEqual(response.status_code, 405)


    def test_experience_star_rating_create_update(self):
        # PUT (create) star rating
        response = self.client.put(f'/experiences/{Test.experience.id}/star_rating/', {'rating': 3}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('rating', response.data)
        self.assertEqual(response.data['rating'], 3)

        response = self.client.get(f'/experiences/{Test.experience.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_star_rating'], 3)

        # PUT (update) star rating
        response = self.client.put(f'/experiences/{Test.experience.id}/star_rating/', {'rating': 5}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('rating', response.data)
        self.assertEqual(response.data['rating'], 5)

        response = self.client.get(f'/experiences/{Test.experience.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_star_rating'], 5)


    def test_experience_cost_rating_create_update(self):
        # PUT (create) cost rating
        response = self.client.put(f'/experiences/{Test.experience.id}/cost_rating/', {'rating': 1}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('rating', response.data)
        self.assertEqual(response.data['rating'], 1)

        response = self.client.get(f'/experiences/{Test.experience.id}/?details=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_cost_rating'], 1)

        # PUT (update) cost rating
        response = self.client.put(f'/experiences/{Test.experience.id}/cost_rating/', {'rating': 4}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('rating', response.data)
        self.assertEqual(response.data['rating'], 4)

        response = self.client.get(f'/experiences/{Test.experience.id}/?details=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_cost_rating'], 4)


    def test_experience_average_star_rating(self):
        ratings = [1, 2, 4]

        # PUT a star rating for user_one
        response = self.client.put(f'/experiences/{Test.experience.id}/star_rating/', {'rating': ratings[0]}, format='json')
        self.assertEqual(response.status_code, 201)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        # PUT a star rating for user_two
        response = self.client.put(f'/experiences/{Test.experience.id}/star_rating/', {'rating': ratings[1]}, format='json')
        self.assertEqual(response.status_code, 201)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_three}')
        # PUT a star rating for user_three
        response = self.client.put(f'/experiences/{Test.experience.id}/star_rating/', {'rating': ratings[2]}, format='json')
        self.assertEqual(response.status_code, 201)

        response = self.client.get(f'/experiences/{Test.experience.id}/')
        self.assertAlmostEqual(response.data['average_star_rating'], sum(ratings) / len(ratings))


    def test_experience_average_cost_rating(self):
        ratings = [4, 2, 3]

        # PUT a cost rating for user_one
        response = self.client.put(f'/experiences/{Test.experience.id}/cost_rating/', {'rating': ratings[0]}, format='json')
        self.assertEqual(response.status_code, 201)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        # PUT a cost rating for user_two
        response = self.client.put(f'/experiences/{Test.experience.id}/cost_rating/', {'rating': ratings[1]}, format='json')
        self.assertEqual(response.status_code, 201)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_three}')
        # PUT a cost rating for user_three
        response = self.client.put(f'/experiences/{Test.experience.id}/cost_rating/', {'rating': ratings[2]}, format='json')
        self.assertEqual(response.status_code, 201)

        response = self.client.get(f'/experiences/{Test.experience.id}/?details=true')
        self.assertAlmostEqual(response.data['average_cost_rating'], sum(ratings) / len(ratings))


    def test_experience_star_rating_min_max(self):
        for rating in range(7):
            response = self.client.put(
                f'/experiences/{Test.experience.id}/star_rating/',
                {'rating': rating},
                format='json')
            if 0 < rating < 6:
                self.assertTrue(
                    response.status_code in [200, 201],
                    msg=f'Rating {rating} should have been 200 range response.')
            else:
                self.assertEqual(
                    response.status_code,
                    400,
                    msg=f'Rating {rating} should have failed with a 400.')


    def test_experience_cost_rating_min_max(self):
        for rating in range(-1, 6):
            response = self.client.put(
                f'/experiences/{Test.experience.id}/cost_rating/',
                {'rating': rating},
                format='json')
            if -1 < rating < 5:
                self.assertTrue(
                    response.status_code in [200, 201],
                    msg=f'Rating {rating} should have been 200 range response.')
            else:
                self.assertEqual(
                    response.status_code,
                    400,
                    msg=f'Rating {rating} should have failed with a 400.')


    def test_playlist_average_star_rating(self):
        ratings = [1, 5, 5]

        # PUT a star rating for user_one
        response = self.client.put(f'/playlists/{Test.playlist.id}/star_rating/', {'rating': ratings[0]}, format='json')
        self.assertEqual(response.status_code, 201)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        # PUT a star rating for user_two
        response = self.client.put(f'/playlists/{Test.playlist.id}/star_rating/', {'rating': ratings[1]}, format='json')
        self.assertEqual(response.status_code, 201)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_three}')
        # PUT a star rating for user_three
        response = self.client.put(f'/playlists/{Test.playlist.id}/star_rating/', {'rating': ratings[2]}, format='json')
        self.assertEqual(response.status_code, 201)

        response = self.client.get(f'/playlists/{Test.playlist.id}/')
        self.assertAlmostEqual(response.data['average_star_rating'], sum(ratings) / len(ratings))


    def test_playlist_average_cost_rating(self):
        ratings = [2, 1, 4]

        # PUT a cost rating for user_one
        response = self.client.put(f'/playlists/{Test.playlist.id}/cost_rating/', {'rating': ratings[0]}, format='json')
        self.assertEqual(response.status_code, 201)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_two}')
        # PUT a cost rating for user_two
        response = self.client.put(f'/playlists/{Test.playlist.id}/cost_rating/', {'rating': ratings[1]}, format='json')
        self.assertEqual(response.status_code, 201)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token_three}')
        # PUT a cost rating for user_three
        response = self.client.put(f'/playlists/{Test.playlist.id}/cost_rating/', {'rating': ratings[2]}, format='json')
        self.assertEqual(response.status_code, 201)

        response = self.client.get(f'/playlists/{Test.playlist.id}/?details=true')
        self.assertAlmostEqual(response.data['average_cost_rating'], sum(ratings) / len(ratings))


    def test_playlist_star_rating_min_max(self):
        for rating in range(7):
            response = self.client.put(
                f'/playlists/{Test.playlist.id}/star_rating/',
                {'rating': rating},
                format='json')
            if 0 < rating < 6:
                self.assertTrue(
                    response.status_code in [200, 201],
                    msg=f'Rating {rating} should have been 200 range response.')
            else:
                self.assertEqual(
                    response.status_code,
                    400,
                    msg=f'Rating {rating} should have failed with a 400.')


    def test_playlist_cost_rating_min_max(self):
        for rating in range(-1, 6):
            response = self.client.put(
                f'/playlists/{Test.playlist.id}/cost_rating/',
                {'rating': rating},
                format='json')
            if -1 < rating < 5:
                self.assertTrue(
                    response.status_code in [200, 201],
                    msg=f'Rating {rating} should have been 200 range response.')
            else:
                self.assertEqual(
                    response.status_code,
                    400,
                    msg=f'Rating {rating} should have failed with a 400.')
