import os
import colorama
from django.conf import settings
from django.test import override_settings
from rest_framework.authtoken.models import Token
from api.models import User
from api.services.sendbird import Sendbird
from . import SilenceableAPITestCase

env = os.environ

# Unit test conversation service SID
@override_settings(
    SENDBIRD_APPLICATION_ID=env.get('SENDBIRD_TESTING_APPLICATION_ID'),
    SENDBIRD_API_TOKEN=env.get('SENDBIRD_TESTING_API_TOKEN'))
class Test(SilenceableAPITestCase):
    user_1: User
    user_2: User
    user_3: User
    should_test_messaging: bool = settings.SENDBIRD_ENABLE_MESSAGING
    token: Token

    # Ran before all tests only once.
    def setUpTestData():
        if not Test.should_test_messaging:
            color = colorama.Fore.MAGENTA
            bright = colorama.Style.BRIGHT
            reset = colorama.Style.RESET_ALL
            print(f"\n{bright}{color}Warning: Messaging not enabled. Messaging tests will be skipped.{reset}")
            return

        Test.user_1 = User.objects.create(
            username= 'test_user_1',
            email = 'testuser1@email.com',
            email_verified = True,
        )
        Test.user_1.set_password('Test1234$')
        Test.user_1.save()
        Test.user_2 = User.objects.create(
            username = 'test_user_2',
            email = 'testuser2@email.com',
            email_verified= True,
        )
        Test.user_2.set_password('Test1234$')
        Test.user_2.save()
        Test.user_3 = User.objects.create(
            username = 'test_user_3',
            email = 'testuser3@email.com',
            email_verified= True,
        )
        Test.user_3.set_password('Test1234$')
        Test.user_3.save()
        Test.token = Token.objects.create(user=Test.user_1)


    # Ran before each test.
    def setUp(self):
        if self.should_test_messaging:
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.token}')
        super().setUp()


    # Ran after all tests only once.
    def tearDown(self):
        if self.should_test_messaging:
            sendBird = Sendbird()
            channels = sendBird.get_all_channels().channels
            for channel in channels:
                sendBird.delete_channel(channel["channel_url"])
        super().tearDown()


    def test_create_group_chat_conversation(self):
        if self.should_test_messaging:
            response = self.client.post('/conversations/',
                {
                    "users": [
                        {"id": Test.user_1.id},
                        {"id": Test.user_2.id},
                        {"id": Test.user_3.id}
                    ],
                    "is_group_chat": True,
                },
                format='json')
            assert response.status_code == 200
            sendbird = Sendbird()
            channel = sendbird.get_channel(response.data)
            assert channel.member_count == 3


    def test_create_direct_messages_conversation(self):
        if self.should_test_messaging:
            response = self.client.post('/conversations/',
                {"users": [
                    {"id": Test.user_1.id},
                    {"id": Test.user_2.id}
                ],
                "is_group_chat": False,
            },
            format='json')
            assert response.status_code == 200
            sendbird = Sendbird()
            channel = sendbird.get_channel(response.data)
            assert channel.member_count == 2

            # Dont create DMs with more than two people
            response = self.client.post('/conversations/',
                    {"users": [
                        {"id": Test.user_2.id},
                        {"id": Test.user_3.id}
                    ],
                    "is_group_chat": False,
                },
                format='json')
            assert response.status_code == 400
