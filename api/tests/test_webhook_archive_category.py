from rest_framework import status
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings

from api.models import (
    Experience,
    User,
)
from . import disable_logging, SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    user: User
    endpoint_url = '/webhooks/category_archived/'

    def setUpTestData():
        Test.user = User.objects.create(
            username='test_user',
            email='test_user@email.com',
            email_verified=True)


    def setUp(self):
        category_groups = [
            [1, 2, 3],
            [2, 3, 4],
            [3, 4, 5],
        ]
        for category_group in category_groups:
            Experience.objects.create(
                name='Test',
                created_by=Test.user,
                categories=category_group)

    @disable_logging
    @override_settings(LIFEFRAME_WEBHOOK_KEY='asdf')
    def test_auth_header(self):
        valid_headers = {
            'HTTP_AUTHORIZATION': f'Bearer {settings.LIFEFRAME_WEBHOOK_KEY}',
        }
        malformed_header_values = [
            f'Bearer{settings.LIFEFRAME_WEBHOOK_KEY}',
            f'Bear {settings.LIFEFRAME_WEBHOOK_KEY}',
            f'{settings.LIFEFRAME_WEBHOOK_KEY}',
            f'Token {settings.LIFEFRAME_WEBHOOK_KEY}',
            f'{settings.LIFEFRAME_WEBHOOK_KEY} Bearer',
            f'Bearer {settings.LIFEFRAME_WEBHOOK_KEY} Bearer',
        ]
        response = self.client.post(Test.endpoint_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        for header_value in malformed_header_values:
            malformed_headers = { 'HTTP_AUTHORIZATION': header_value }
            response = self.client.post(Test.endpoint_url, **malformed_headers)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(Test.endpoint_url, **valid_headers)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    @override_settings(LIFEFRAME_WEBHOOK_KEY='asdf')
    def test_update_success_response_code(self):
        headers = {
            'HTTP_AUTHORIZATION': f'Bearer {settings.LIFEFRAME_WEBHOOK_KEY}',
        }
        data = {
            'reason': 0,
            'category': {
                'id': 0,
                'name': 'Animals',
                'parent_id': None,
                'parent_name': None,
                'has_children': True,
                'relevant_weight': None,
                'search_similarity': None,
                'archived': True,
                'forwarded_to': None,
            },
        }
        response = self.client.post(
            Test.endpoint_url,
            data=data,
            format='json',
            **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    @disable_logging
    @override_settings(LIFEFRAME_WEBHOOK_KEY='asdf')
    def test_update_no_changes(self):
        headers = {
            'HTTP_AUTHORIZATION': f'Bearer {settings.LIFEFRAME_WEBHOOK_KEY}',
        }
        data = {
            'reason': 0,
            'category': {
                'id': 0,
                'name': 'Animals',
                'parent_id': None,
                'parent_name': None,
                'has_children': True,
                'relevant_weight': None,
                'search_similarity': None,
                'archived': True,
                'forwarded_to': None,
            },
        }
        response = self.client.post(
            Test.endpoint_url,
            data=data,
            format='json',
            **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        call_command('consume_category_archive_spool')
        expected_dicts = [
            { 'category_id': 1, 'count': 1 },
            { 'category_id': 2, 'count': 2 },
            { 'category_id': 3, 'count': 3 },
            { 'category_id': 4, 'count': 2 },
            { 'category_id': 5, 'count': 1 },
        ]
        for expected in expected_dicts:
            category_id = expected['category_id']
            count = Experience.objects \
                .filter(categories__contains=[category_id]) \
                .count()
            self.assertEqual(count, expected['count'])


    @disable_logging
    @override_settings(LIFEFRAME_WEBHOOK_KEY='asdf')
    def test_update_no_parent(self):
        headers = {
            'HTTP_AUTHORIZATION': f'Bearer {settings.LIFEFRAME_WEBHOOK_KEY}',
        }
        data = {
            'reason': 0,
            'category': {
                'id': 2,
                'name': 'Dogs',
                'parent_id': None,
                'parent_name': 'Animals',
                'has_children': True,
                'relevant_weight': None,
                'search_similarity': None,
                'archived': True,
                'forwarded_to': None,
            },
        }
        response = self.client.post(
            Test.endpoint_url,
            data=data,
            format='json',
            **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        call_command('consume_category_archive_spool')
        expected_dicts = [
            { 'category_id': 1, 'count': 1 },
            { 'category_id': 2, 'count': 0 },
            { 'category_id': 3, 'count': 3 },
            { 'category_id': 4, 'count': 2 },
            { 'category_id': 5, 'count': 1 },
        ]
        for expected in expected_dicts:
            category_id = expected['category_id']
            count = Experience.objects \
                .filter(categories__contains=[category_id]) \
                .count()
            self.assertEqual(count, expected['count'])


    @disable_logging
    @override_settings(LIFEFRAME_WEBHOOK_KEY='asdf')
    def test_update_to_parent(self):
        headers = {
            'HTTP_AUTHORIZATION': f'Bearer {settings.LIFEFRAME_WEBHOOK_KEY}',
        }
        data = {
            'reason': 0,
            'category': {
                'id': 2,
                'name': 'Dogs',
                'parent_id': 6,
                'parent_name': 'Animals',
                'has_children': True,
                'relevant_weight': None,
                'search_similarity': None,
                'archived': True,
                'forwarded_to': None,
            },
        }
        response = self.client.post(
            Test.endpoint_url,
            data=data,
            format='json',
            **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        call_command('consume_category_archive_spool')
        expected_dicts = [
            { 'category_id': 1, 'count': 1 },
            { 'category_id': 2, 'count': 0 },
            { 'category_id': 3, 'count': 3 },
            { 'category_id': 4, 'count': 2 },
            { 'category_id': 5, 'count': 1 },
            { 'category_id': 6, 'count': 2 },
        ]
        for expected in expected_dicts:
            category_id = expected['category_id']
            count = Experience.objects \
                .filter(categories__contains=[category_id]) \
                .count()
            self.assertEqual(count, expected['count'])


    @disable_logging
    @override_settings(LIFEFRAME_WEBHOOK_KEY='asdf')
    def test_update_to_forward_to(self):
        headers = {
            'HTTP_AUTHORIZATION': f'Bearer {settings.LIFEFRAME_WEBHOOK_KEY}',
        }
        data = {
            'reason': 0,
            'category': {
                'id': 2,
                'name': 'Dogs',
                'parent_id': None,
                'parent_name': None,
                'has_children': True,
                'relevant_weight': None,
                'search_similarity': None,
                'archived': True,
                'forwarded_to': 6,
            },
        }
        response = self.client.post(
            Test.endpoint_url,
            data=data,
            format='json',
            **headers)
        call_command('consume_category_archive_spool')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_dicts = [
            { 'category_id': 1, 'count': 1 },
            { 'category_id': 2, 'count': 0 },
            { 'category_id': 3, 'count': 3 },
            { 'category_id': 4, 'count': 2 },
            { 'category_id': 5, 'count': 1 },
            { 'category_id': 6, 'count': 2 },
        ]
        for expected in expected_dicts:
            category_id = expected['category_id']
            count = Experience.objects \
                .filter(categories__contains=[category_id]) \
                .count()
            self.assertEqual(count, expected['count'])
