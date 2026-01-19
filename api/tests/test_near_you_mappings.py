from rest_framework import status
from rest_framework.authtoken.models import Token

from api.models import (
    Experience,
    NearYouMapping,
    User,
)
from api.utils.file_handling import split_file_url
from api.validators import is_uuid4
from . import SilenceableAPITestCase

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
        Test.experience_one = Experience.objects.create(
            name = 'test_experience_1',
            latitude=75.32,
            longitude=-59.6,
            highlight_image='fake_image_url_just_for_testing.jpg',
            created_by = Test.user_one)
        Test.experience_two = Experience.objects.create(
            name = 'test_experience_2',
            latitude=-70.5,
            longitude=105.6,
            created_by = Test.user_two)
        Test.experience_three = Experience.objects.create(
            name = 'test_experience_3',
            latitude=13.05,
            longitude=172.68,
            created_by = Test.user_one)
        Test.experience_four = Experience.objects.create(
            name = 'test_experience_4',
            latitude=13.03,
            longitude=172.91,
            highlight_image='another_fake_image_url_just_for_testing.png',
            created_by = Test.user_two)
        Test.experience_five = Experience.objects.create(
            name = 'test_experience_5',
            latitude=12.98,
            longitude=172.85,
            created_by = Test.user_one)
        Test.token = Token.objects.create(user=Test.user_one)
        Test.latitude = 13.01
        Test.longitude = 172.78


    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')


    def test_near_you(self):
        response = self.client.get(
            f'/discover_feed/near/?latitude={Test.latitude}&longitude={Test.longitude}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertIsNone(response.data['next_page'])
        self.assertIsNone(response.data['previous_page'])
        near_exps = response.data['results']
        self.assertEqual(len(near_exps), 3)
        self.assertLessEqual(near_exps[0]['distance'], near_exps[1]['distance'])
        self.assertLessEqual(near_exps[1]['distance'], near_exps[2]['distance'])


    def test_near_you_mapping(self):
        # Should 404 because no lat & lng supplied, and there are is no default NearYouMapping
        response = self.client.get(f'/discover_feed/near_you_mapping/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Empty latitude and longitude strings should also 404
        response = self.client.get(
            f'/discover_feed/near_you_mapping/?latitude=     &longitude=  ')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # No experiences near the latitude and longitude and no NearYouMappings should 404
        response = self.client.get(
            f'/discover_feed/near_you_mapping/?latitude=0.0&longitude=0.0')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Should get a NearYouMapping created with the image of the near experience
        response = self.client.get(
            f'/discover_feed/near_you_mapping/?latitude={Test.latitude}&longitude={Test.longitude}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        split_mapping_image_url = split_file_url(response.data['image'])
        # The name should have been converted to a UUID on saving the Experience
        self.assertTrue(is_uuid4(split_mapping_image_url['name']))
        # It should've kept its extension
        self.assertEqual(split_mapping_image_url['extension'], 'png')
        near_exp_with_image = Experience.objects.get(name='test_experience_4')
        self.assertTrue(str(near_exp_with_image.highlight_image)[1:], response.data['image'])
        self.assertEqual(response.data['overlay_opacity'], 0.2)
        self.assertEqual(response.data['text_color'], '#FFFFFF')
        self.assertEqual(response.data['background_color'], '#000000')

        NearYouMapping.objects.create(
            is_default=True,
            image='fake_image_url_that_is_going_to_be_converted_to_a_UUID_anyway.jpg',
            overlay_opacity=0.4,
            text_color='#EEDDCC',
            background_color='#334455',
        )

        # Should not 404 anymore because there is a default NearYouMapping
        response = self.client.get(f'/discover_feed/near_you_mapping/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        split_mapping_image_url = split_file_url(response.data['image'])
        # The name should have been converted to a UUID on saving the Experience
        self.assertTrue(is_uuid4(split_mapping_image_url['name']))
        # It should've kept its extension
        self.assertEqual(split_mapping_image_url['extension'], 'jpg')
        self.assertEqual(response.data['overlay_opacity'], 0.4)
        self.assertEqual(response.data['text_color'], '#EEDDCC')
        self.assertEqual(response.data['background_color'], '#334455')

        # Should not 404 anymore because there is a default NearYouMapping
        response = self.client.get(
            f'/discover_feed/near_you_mapping/?latitude=     &longitude=  ')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        split_mapping_image_url = split_file_url(response.data['image'])
        # The name should have been converted to a UUID on saving the Experience
        self.assertTrue(is_uuid4(split_mapping_image_url['name']))
        # It should've kept its extension
        self.assertEqual(split_mapping_image_url['extension'], 'jpg')
        self.assertEqual(response.data['overlay_opacity'], 0.4)
        self.assertEqual(response.data['text_color'], '#EEDDCC')
        self.assertEqual(response.data['background_color'], '#334455')

        # No experiences near the given latitude and longitude
        # should find the default NearYouMapping
        response = self.client.get(
            f'/discover_feed/near_you_mapping/?latitude=0.0&longitude=0.0')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        split_mapping_image_url = split_file_url(response.data['image'])
        # The name should have been converted to a UUID on saving the Experience
        self.assertTrue(is_uuid4(split_mapping_image_url['name']))
        # It should've kept its extension
        self.assertEqual(split_mapping_image_url['extension'], 'jpg')
        self.assertEqual(response.data['overlay_opacity'], 0.4)
        self.assertEqual(response.data['text_color'], '#EEDDCC')
        self.assertEqual(response.data['background_color'], '#334455')

        bigger_radius_mapping = NearYouMapping.objects.create(
            image='fake_image_url_that_is_going_to_be_converted_to_a_UUID_anyway.png',
            overlay_opacity=0.28,
            text_color='#AACCEE',
            background_color='#008899',
            latitude=13.015,
            longitude=172.785,
            radius=100,
        )

        smaller_radius_mapping = NearYouMapping.objects.create(
            image='fake_image_url_that_is_going_to_be_converted_to_a_UUID_anyway.jpg',
            overlay_opacity=0.35,
            text_color='#339933',
            background_color='#AA44CC',
            latitude=13.018,
            longitude=172.788,
            radius=10,
        )

        # Delete all experiences so no nearby experiences anymore
        Experience.objects.all().delete()

        # The lat & lng supplied are within the circle of both NearYouMapping objects,
        # so it should return the one with the smaller radius
        response = self.client.get(
            f'/discover_feed/near_you_mapping/?latitude={Test.latitude}&longitude={Test.longitude}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        split_mapping_image_url = split_file_url(response.data['image'])
        # The name should have been converted to a UUID on saving the Experience
        self.assertTrue(is_uuid4(split_mapping_image_url['name']))
        # It should've kept its extension
        self.assertEqual(split_mapping_image_url['extension'], 'jpg')
        self.assertEqual(response.data['overlay_opacity'], smaller_radius_mapping.overlay_opacity)
        self.assertNotEqual(response.data['overlay_opacity'], bigger_radius_mapping.overlay_opacity)
        self.assertEqual(response.data['text_color'], smaller_radius_mapping.text_color)
        self.assertNotEqual(response.data['text_color'], bigger_radius_mapping.text_color)
        self.assertEqual(response.data['background_color'], smaller_radius_mapping.background_color)
        self.assertNotEqual(response.data['background_color'], bigger_radius_mapping.background_color)
