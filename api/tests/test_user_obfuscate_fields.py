from api.models import (
    User,
)
from . import disable_logging, SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    user: User

    def setUpTestData():
        Test.user = User.objects.create(
            username='asdf',
            email='testuser@email.com',
            email_verified=True)

    def test_phone_obfuscate(self):
        self.assertIsNone(Test.user.phone)
        self.assertIsNone(Test.user.obfuscated_phone)
        Test.user.phone = '(801) 123-4567'
        self.assertEqual(Test.user.obfuscated_phone, '(***) ***-*567')

    def test_email_obfuscate(self):
        self.assertEqual(Test.user.obfuscated_email, 't******r@email.com')
