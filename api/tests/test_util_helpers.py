from . import SilenceableAPITestCase
from api.models import (
    User,
)
from api.utils import (
    file_handling,
    username_from_email,
)

class Test(SilenceableAPITestCase):
    def test_file_handling_split_path(self):
        result = file_handling.split_file_url('/path/name.ext')
        self.assertEqual(result['path'], '/path/')
        self.assertEqual(result['name'], 'name')
        self.assertEqual(result['extension'], 'ext')

        result = file_handling.split_file_url('name.ext')
        self.assertEqual(result['path'], '')
        self.assertEqual(result['name'], 'name')
        self.assertEqual(result['extension'], 'ext')

        result = file_handling.split_file_url('/path/name.extra.ext')
        self.assertEqual(result['path'], '/path/')
        self.assertEqual(result['name'], 'name.extra')
        self.assertEqual(result['extension'], 'ext')

        result = file_handling.split_file_url('/path/.name.ext')
        self.assertEqual(result['path'], '/path/')
        self.assertEqual(result['name'], '.name')
        self.assertEqual(result['extension'], 'ext')

        result = file_handling.split_file_url('/path/.name')
        self.assertEqual(result['path'], '/path/')
        self.assertEqual(result['name'], '.name')
        self.assertEqual(result['extension'], '')

        result = file_handling.split_file_url('/path/name')
        self.assertEqual(result['path'], '/path/')
        self.assertEqual(result['name'], 'name')
        self.assertEqual(result['extension'], '')

        result = file_handling.split_file_url('name.extra.ext')
        self.assertEqual(result['path'], '')
        self.assertEqual(result['name'], 'name.extra')
        self.assertEqual(result['extension'], 'ext')

        result = file_handling.split_file_url('.name.ext')
        self.assertEqual(result['path'], '')
        self.assertEqual(result['name'], '.name')
        self.assertEqual(result['extension'], 'ext')

        result = file_handling.split_file_url('/name.ext')
        self.assertEqual(result['path'], '/')
        self.assertEqual(result['name'], 'name')
        self.assertEqual(result['extension'], 'ext')

        result = file_handling.split_file_url('/.name')
        self.assertEqual(result['path'], '/')
        self.assertEqual(result['name'], '.name')
        self.assertEqual(result['extension'], '')

        result = file_handling.split_file_url('.name')
        self.assertEqual(result['path'], '')
        self.assertEqual(result['name'], '.name')
        self.assertEqual(result['extension'], '')

        result = file_handling.split_file_url('')
        self.assertEqual(result['path'], '')
        self.assertEqual(result['name'], '')
        self.assertEqual(result['extension'], '')

        result = file_handling.split_file_url(None)
        self.assertEqual(result['path'], '')
        self.assertEqual(result['name'], '')
        self.assertEqual(result['extension'], '')

    def test_username_from_email(self):
        user = User(
            username = 'user',
            email = 'user@email.com',
            email_verified = True,
        )
        user.save()
        username = username_from_email('user@email2.com')
        self.assertEqual(username, 'user2')
        user2 = User(
            username = 'user2',
            email = 'user2@email.com',
            email_verified = True,
        )
        user2.save()
        username = username_from_email('user@email2.com')
        self.assertEqual(username, 'user3')
        user3 = User(
            username = 'user3',
            email = 'user3@email.com',
            email_verified = True,
        )
        user3.save()
        username = username_from_email('user@email2.com')
        self.assertEqual(username, 'user4')
        user4 = User(
            username = 'user4',
            email = 'user4@email.com',
            email_verified = True,
        )
        user4.save()
        username = username_from_email('user@email2.com')
        self.assertEqual(username, 'user5')

        username = username_from_email('user2@email.com')
        self.assertEqual(username, 'user22')
