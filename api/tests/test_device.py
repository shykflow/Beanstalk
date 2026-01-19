from datetime import date
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.authtoken.models import Token

from api.models import Device, User
from api.enums import DeviceOS
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    user_one: User
    user_two: User
    user_three: User
    user_four: User
    device_one: Device
    device_two: Device
    device_three: Device
    token: Token

    def setUpTestData():
        Test.user_one = User.objects.create(
            username = 'test_user_one',
            email = 'testuserone@email.com',
            email_verified = False,
        )
        Test.user_two = User.objects.create(
            username = 'test_user_two',
            email = 'testusertwo@email.com',
            email_verified = False,
        )
        Test.user_three = User.objects.create(
            username = 'test_user_three',
            email = 'testuserthree@email.com',
            email_verified = False,
        )
        Test.user_four = User.objects.create(
            username = 'test_user_four',
            email = 'testuserfour@email.com',
            email_verified = False,
        )
        Test.device_one = Device.objects.create(
            user=Test.user_one,
            token='device_one_token',
        )
        Test.device_two = Device.objects.create(
            user=Test.user_two,
            token='     ',
        )
        Test.device_three = Device.objects.create(
            user=Test.user_three,
            token='',
        )
        Test.token = Token.objects.create(user=Test.user_one)


    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')


    def test_extra_attributes(self):
        token = 'token_test_extra_attributes'
        details = {'detail_one': 'this is a detail'}
        device_os = DeviceOS.ANDROID.value
        minutes_offset = -360
        response = self.client.post('/devices/update_fcm_token/', {
            'token': token,
            'details': details,
            'os': device_os,
            'minutes_offset': minutes_offset,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        device = Device.objects.get(token=token)
        self.assertEqual(device.details['detail_one'], details['detail_one'])
        self.assertEqual(device.os, device_os)
        self.assertEqual(device.minutes_offset, minutes_offset)


    def test_update_fcm_token(self):
        # Valid token should 200 and update the details
        before_details = Test.device_one.details
        response = self.client.post('/devices/update_fcm_token/', {
            'token': Test.device_one.token,
            'details': {'detail_one': 'this is a detail'},
        }, format='json')
        self.assertEqual(response.status_code, 200)
        Test.device_one.refresh_from_db()
        self.assertNotEqual(before_details, Test.device_one.details)

        # Empty space token should 400 and not update the details
        before_details = Test.device_two.details
        response = self.client.post('/devices/update_fcm_token/', {
            'token': Test.device_two.token,
            'details': {'detail_two': 'this is a detail'},
        }, format='json')
        self.assertEqual(response.status_code, 400)
        Test.device_two.refresh_from_db()
        self.assertEqual(before_details, Test.device_two.details)

        # Empty token should 400 and not update the details
        before_details = Test.device_three.details
        response = self.client.post('/devices/update_fcm_token/', {
            'token': Test.device_three.token,
            'details': {'detail_three': 'this is a detail'},
        }, format='json')
        self.assertEqual(response.status_code, 400)
        Test.device_three.refresh_from_db()
        self.assertEqual(before_details, Test.device_three.details)

        # No existing device for the token should 200 and create a new device
        with self.assertRaises(ObjectDoesNotExist):
            Device.objects.get(token='nonexistent_device_token')
        response = self.client.post('/devices/update_fcm_token/', {
            'token': 'nonexistent_device_token',
            'details': {'detail_three': 'this is a detail'},
        }, format='json')
        self.assertEqual(response.status_code, 200)
        created_device: Device = Device.objects.get(token='nonexistent_device_token')
        self.assertEqual(Test.user_one, created_device.user)
        self.assertEqual('nonexistent_device_token', created_device.token)
        self.assertEqual(date.today(), created_device.last_check_in)
        self.assertEqual({'detail_three': 'this is a detail'}, created_device.details)
