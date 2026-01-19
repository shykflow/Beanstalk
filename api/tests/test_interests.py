from rest_framework.authtoken.models import Token

from api.models import Interest, User
from . import SilenceableAPITestCase

# Notes on the difference between setUpTestData() and setUp()
# https://stackoverflow.com/questions/29428894/django-setuptestdata-vs-setup

class Test(SilenceableAPITestCase):
    user: User
    token: Token

    # Ran before all tests only once.
    def setUpTestData():
        # Create a user
        Test.user = User.objects.create(
            username = 'test_user',
            email = 'testuser@email.com',
            email_verified = True,
        )
        Test.token = Token.objects.create(user=Test.user)


    # Ran before each test.
    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')


    def test_retrieve_model(self):
        interest: Interest = Interest.objects.create(
            user=Test.user,
            category=1
        )
        response = self.client.get(f'/interests/{interest.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['category'], 1)

    def test_get_interests(self):
        response = self.client.get('/interests/')
        assert response.status_code == 200


    def test_set_interests(self):
        # Add 3 interests
        data = [
            { 'category': 1 },
            { 'category': 2 },
            { 'category': 3 },
            # { 'category': 4 },
        ]
        response = self.client.put('/interests/batch_update/', data, format='json')
        assert response.status_code == 200
        response = self.client.get('/interests/')
        assert response.status_code == 200
        for d in response.data:
            assert d.get('id') is not None
        assert len([x for x in response.data if x['category'] == 1]) == 1
        assert len([x for x in response.data if x['category'] == 2]) == 1
        assert len([x for x in response.data if x['category'] == 3]) == 1
        assert len([x for x in response.data if x['category'] == 4]) == 0

        # Remove an interest
        data = [
            { 'category': 1 },
            # { 'category': 2 },
            { 'category': 3 },
            # { 'category': 4 },
        ]
        response = self.client.put('/interests/batch_update/', data, format='json')
        assert response.status_code == 200
        response = self.client.get('/interests/')
        assert response.status_code == 200
        assert len([x for x in response.data if x['category'] == 1]) == 1
        assert len([x for x in response.data if x['category'] == 2]) == 0
        assert len([x for x in response.data if x['category'] == 3]) == 1
        assert len([x for x in response.data if x['category'] == 4]) == 0

        # Add a new interest
        data = [
            { 'category': 1 },
            # { 'category': 2 },
            { 'category': 3 },
            { 'category': 4 },
        ]
        response = self.client.put('/interests/batch_update/', data, format='json')
        assert response.status_code == 200
        response = self.client.get('/interests/')
        assert response.status_code == 200
        assert len([x for x in response.data if x['category'] == 1]) == 1
        assert len([x for x in response.data if x['category'] == 2]) == 0
        assert len([x for x in response.data if x['category'] == 3]) == 1
        assert len([x for x in response.data if x['category'] == 4]) == 1

        # Add an interest that was previously removed
        data = [
            { 'category': 1 },
            { 'category': 2 },
            { 'category': 3 },
            { 'category': 4 },
        ]
        response = self.client.put('/interests/batch_update/', data, format='json')
        assert response.status_code == 200
        response = self.client.get('/interests/')
        assert response.status_code == 200
        assert len([x for x in response.data if x['category'] == 1]) == 1
        assert len([x for x in response.data if x['category'] == 2]) == 1
        assert len([x for x in response.data if x['category'] == 3]) == 1
        assert len([x for x in response.data if x['category'] == 4]) == 1
