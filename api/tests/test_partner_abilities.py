import json

from rest_framework import status
from rest_framework.authtoken.models import Token

from api.enums import UserType
from api.models import Playlist, Experience, User
from api.testing_overrides import GlobalTestCredentials, TestFiles

from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    regular_user: User
    partner_user: User

    regular_user_token: Token
    partner_user_token: Token

    links: dict[str, str] = {
        'reservation': 'https://reservations.com',
        'menu': 'https://menus.com',
        'purchase': 'https://purchase.com',
    }


    def setUpTestData():
        Test.regular_user = User.objects.create(
            username='regular',
            email='regular@email.com',
            email_verified=True,
            user_type=UserType.UNVERIFIED)
        Test.partner_user = User.objects.create(
            username='partner',
            email='partner@email.com',
            email_verified=True,
            user_type=UserType.PARTNER)
        Test.regular_user_token = Token.objects.create(
            user=Test.regular_user)
        Test.partner_user_token = Token.objects.create(
            user=Test.partner_user)


    def test_partner_user_fields_on_create(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {Test.partner_user_token}')
        response = self.client.post('/experiences/', {
            'json': json.dumps({
                'name': 'a',
                'description': 'a',
                'reservation_link': Test.links['reservation'],
                'menu_link': Test.links['menu'],
                'purchase_link': Test.links['purchase'],
            })
        })
        exp_dict: dict[str, any] = response.data
        exp: Experience = Experience.objects.get(id=exp_dict['id'])
        self.assertEqual(exp.reservation_link, Test.links['reservation'])
        self.assertEqual(exp.menu_link, Test.links['menu'])
        self.assertEqual(exp.purchase_link, Test.links['purchase'])


    def test_regular_user_fields_on_create(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {Test.regular_user_token}')
        response = self.client.post('/experiences/', {
            'json': json.dumps({
                'name': 'a',
                'description': 'a',
                'reservation_link': Test.links['reservation'],
            })
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.post('/experiences/', {
            'json': json.dumps({
                'name': 'a',
                'description': 'a',
                'menu_link': Test.links['menu'],
            })
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.post('/experiences/', {
            'json': json.dumps({
                'name': 'a',
                'description': 'a',
                'purchase_link': Test.links['purchase'],
            })
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_partner_user_fields_on_update(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {Test.partner_user_token}')
        exp: Experience = Experience.objects.create(
            created_by=Test.partner_user,
            name='a',
            description='a')
        response = self.client.put(f'/experiences/{exp.id}/', {
            'json': json.dumps({
                'name': 'a',
                'description': 'a',
                'reservation_link': Test.links['reservation'],
                'menu_link': Test.links['menu'],
                'purchase_link': Test.links['purchase']
            })
        })
        exp.refresh_from_db()
        self.assertEqual(exp.reservation_link, Test.links['reservation'])
        self.assertEqual(exp.menu_link, Test.links['menu'])
        self.assertEqual(exp.purchase_link, Test.links['purchase'])


    def test_regular_user_fields_on_update(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {Test.regular_user_token}')

        exp: Experience = Experience.objects.create(
            created_by=Test.regular_user,
            name='a',
            description='a')
        self.assertIsNone(exp.reservation_link)
        self.assertIsNone(exp.menu_link)

        # Update with partner links
        response = self.client.put(f'/experiences/{exp.id}/', {
            'json': json.dumps({
                'name': 'a',
                'description': 'a',
                'reservation_link': Test.links['reservation'],
            })
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.put(f'/experiences/{exp.id}/', {
            'json': json.dumps({
                'name': 'a',
                'description': 'a',
                'menu_link': Test.links['menu'],
            })
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.put(f'/experiences/{exp.id}/', {
            'json': json.dumps({
                'name': 'a',
                'description': 'a',
                'purchase_link': Test.links['purchase'],
            })
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)



