import pyotp
from django.conf import settings
from requests.exceptions import ConnectionError
from rest_framework import status
from rest_framework.authtoken.models import Token

from api.models import (
    User,
    MFAConfig,
    MFAType,
)
from api.enums import (
    CustomHttpStatusCodes,
)
from api.utils import random_code
from api.utils.authentication import (
    MFAUtils,
    MFAResult,
)
from lf_service.util import LifeFrameUtilService
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    should_fake_life_frame_id: bool
    user: User
    token: Token
    password = 'Test1234$'
    intervals = {
        'sms':           settings.OTP_TIMEOUTS['sms']['interval'],
        'email':         settings.OTP_TIMEOUTS['email']['interval'],
        'authenticator': settings.OTP_TIMEOUTS['authenticator']['interval'],
    }


    def setUpTestData():
        try:
            response = LifeFrameUtilService().healthcheck()
            if response.status_code != 200:
                raise ConnectionError
            Test.should_fake_life_frame_id = False
        except ConnectionError:
            Test.should_fake_life_frame_id = True
        Test.user = User.objects.create(
            username='asdf',
            email='asdf@email.com',
            is_staff=True,
            email_verified=True,
            phone="(801) 123-4567")
        if Test.should_fake_life_frame_id:
            Test.user.life_frame_id = 'fake'
        Test.token = Token.objects.create(user=Test.user)
        Test.user.set_password(Test.password)
        Test.user.save()


    def generate_seeds_otps_sets(self) -> tuple[dict[str, None], dict[str, None]]:
        seeds = {
            'sms': None,
            'email': None,
            'authenticator': None,
        }
        otps = {
            'sms': None,
            'email': None,
            'authenticator': None,
        }
        # Ensure there's only a single pass code for each config
        # (Not enforcing each, just making sure the results match)
        duplicate_outcomes_exist = True
        while duplicate_outcomes_exist:
            seeds['sms'] = pyotp.random_base32()
            seeds['email'] = pyotp.random_base32()
            seeds['authenticator'] = pyotp.random_base32()
            otps['sms'] = pyotp.TOTP(
                seeds['sms'],
                interval=Test.intervals['sms']).now()
            otps['email'] = pyotp.TOTP(
                seeds['email'],
                interval=Test.intervals['email']).now()
            otps['authenticator'] = pyotp.TOTP(
                seeds['authenticator'],
                interval=Test.intervals['authenticator']).now()
            values = list(set(otps.values()))
            if len(values) == 3:
                duplicate_outcomes_exist = False
        return seeds, otps


    def test_generate_seeds_otps_sets(self):
        # Test the helper function, make sure the seeds and otps it generates
        # are good for testing.
        # This makes sure this test won't break.
        seeds, otps = self.generate_seeds_otps_sets()
        totp = pyotp.TOTP(seeds['sms'], interval=Test.intervals['sms'])
        self.assertEqual(otps['sms'], totp.now())
        totp = pyotp.TOTP(seeds['email'], interval=Test.intervals['email'])
        self.assertEqual(otps['email'], totp.now())
        totp = pyotp.TOTP(seeds['authenticator'], interval=Test.intervals['authenticator'])
        self.assertEqual(otps['authenticator'], totp.now())


    def test_helper_methods_user_has_no_configs(self):
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, '')
        self.assertEqual(result, MFAResult.OTP_REQUIRED)
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, '123456')
        self.assertEqual(result, MFAResult.INVALID)

    def test_helper_methods_no_otp_given(self):
        seeds, otps = self.generate_seeds_otps_sets()
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.SMS,
            seed=seeds['sms'])
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.EMAIL,
            seed=seeds['email'])
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.AUTHENTICATOR,
            seed=seeds['authenticator'])
        # No passcode given
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, '')
        self.assertEqual(result, MFAResult.OTP_REQUIRED)


    def test_helper_methods_allowed_types(self):
        '''
        validate_user_otp() takes an optional "allowed_types" parameter,
        this test makes sure that when a valid otp is sent in for an
        existing MFAConfig on a user, if it isn't in the allowed_types
        it should still fail.
        '''
        seeds, otps = self.generate_seeds_otps_sets()
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.SMS,
            seed=seeds['sms'])
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.EMAIL,
            seed=seeds['email'])
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.AUTHENTICATOR,
            seed=seeds['authenticator'])
        # SMS
        allowed_types_lists = [
            [],
            [MFAType.EMAIL],
            [MFAType.AUTHENTICATOR],
            [MFAType.EMAIL, MFAType.AUTHENTICATOR],
        ]
        for allowed_types in allowed_types_lists:
            result, mfa_config = MFAUtils.validate_user_otp(
                Test.user,
                otps['sms'],
                allowed_types=allowed_types)
            self.assertEqual(result, MFAResult.INVALID)
        # EMAIL
        allowed_types_lists = [
            [],
            [MFAType.SMS],
            [MFAType.AUTHENTICATOR],
            [MFAType.SMS, MFAType.AUTHENTICATOR],
        ]
        for allowed_types in allowed_types_lists:
            result, mfa_config = MFAUtils.validate_user_otp(
                Test.user,
                otps['email'],
                allowed_types=allowed_types)
            self.assertEqual(result, MFAResult.INVALID)
        # AUTHENTICATOR
        allowed_types_lists = [
            [],
            [MFAType.SMS],
            [MFAType.EMAIL],
            [MFAType.SMS, MFAType.EMAIL],
        ]
        for allowed_types in allowed_types_lists:
            result, mfa_config = MFAUtils.validate_user_otp(
                Test.user,
                otps['authenticator'],
                allowed_types=allowed_types)
            self.assertEqual(result, MFAResult.INVALID)


    def test_helper_methods_configs_not_verified(self):
        # Makes sure non-verified configs don't get used
        seeds, otps = self.generate_seeds_otps_sets()
        # SMS
        sms_config = MFAConfig.objects.create(
            user=Test.user,
            type=MFAType.SMS,
            seed=seeds['sms'])
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, otp=otps['sms'])
        self.assertEqual(result, MFAResult.INVALID)
        sms_config.verified = True
        sms_config.save()
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, otp=otps['sms'])
        self.assertEqual(result, MFAResult.AUTHENTICATED_SMS)
        # Email
        email_config = MFAConfig.objects.create(
            user=Test.user,
            type=MFAType.EMAIL,
            seed=seeds['email'])
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, otp=otps['email'])
        self.assertEqual(result, MFAResult.INVALID)
        email_config.verified = True
        email_config.save()
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, otp=otps['email'])
        self.assertEqual(result, MFAResult.AUTHENTICATED_EMAIL)
        # Authenticator
        authenticator_config = MFAConfig.objects.create(
            user=Test.user,
            type=MFAType.AUTHENTICATOR,
            seed=seeds['authenticator'])
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, otp=otps['authenticator'])
        self.assertEqual(result, MFAResult.INVALID)
        authenticator_config.verified = True
        authenticator_config.save()
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, otp=otps['authenticator'])
        self.assertEqual(result, MFAResult.AUTHENTICATED_AUTHENTICATOR)


    def test_helper_methods_sms_config(self):
        interval = settings.OTP_TIMEOUTS['sms']['interval']
        seed = pyotp.random_base32()
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.SMS,
            seed=seed)
        # No passcode given
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, '')
        self.assertEqual(result, MFAResult.OTP_REQUIRED)
        # Valid passcode given
        totp = pyotp.TOTP(seed, interval=interval)
        valid_otp = totp.now()
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, valid_otp)
        self.assertEqual(result, MFAResult.AUTHENTICATED_SMS)
        invalid_otp = '111111'
        # In the extremely unlikely case 111111 was the valid otp
        # use a different otp
        if invalid_otp == valid_otp:
            invalid_otp = '111112'
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, invalid_otp)
        self.assertEqual(result, MFAResult.INVALID)


    def test_helper_methods_email_config(self):
        interval = settings.OTP_TIMEOUTS['email']['interval']
        seed = pyotp.random_base32()
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.EMAIL,
            seed=seed)
        # No passcode given
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, '')
        self.assertEqual(result, MFAResult.OTP_REQUIRED)
        # Valid passcode given
        totp = pyotp.TOTP(seed, interval=interval)
        valid_otp = totp.now()
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, valid_otp)
        self.assertEqual(result, MFAResult.AUTHENTICATED_EMAIL)
        invalid_otp = '111111'
        # In the extremely unlikely case 111111 was the valid otp
        # use a different otp
        if invalid_otp == valid_otp:
            invalid_otp = '111112'
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, invalid_otp)
        self.assertEqual(result, MFAResult.INVALID)


    def test_helper_methods_authenticator_config(self):
        interval = settings.OTP_TIMEOUTS['authenticator']['interval']
        seed = pyotp.random_base32()
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.AUTHENTICATOR,
            seed=seed)
        # No passcode given
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, '')
        self.assertEqual(result, MFAResult.OTP_REQUIRED)
        # Valid passcode given
        totp = pyotp.TOTP(seed, interval=interval)
        valid_otp = totp.now()
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, valid_otp)
        self.assertEqual(result, MFAResult.AUTHENTICATED_AUTHENTICATOR)
        invalid_otp = '111111'
        # In the extremely unlikely case 111111 was the valid otp
        # use a different otp
        if invalid_otp == valid_otp:
            invalid_otp = '111112'
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, invalid_otp)
        self.assertEqual(result, MFAResult.INVALID)


    def test_helper_methods_user_has_multiple_config(self):
        seeds, otps = self.generate_seeds_otps_sets()
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.SMS,
            seed=seeds['sms'])
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.EMAIL,
            seed=seeds['email'])
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.AUTHENTICATOR,
            seed=seeds['authenticator'])
        # sms
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, otps['sms'])
        self.assertEqual(result, MFAResult.AUTHENTICATED_SMS)
        # email
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, otps['email'])
        self.assertEqual(result, MFAResult.AUTHENTICATED_EMAIL)
        # sms
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, otps['authenticator'])
        self.assertEqual(result, MFAResult.AUTHENTICATED_AUTHENTICATOR)
        # No passcode given
        result, mfa_config = MFAUtils.validate_user_otp(Test.user, '')
        self.assertEqual(result, MFAResult.OTP_REQUIRED)


    def test_endpoint_request_otp_no_method_specified(self):
        endpoint = '/users/request_otp/'
        # No method specified (should be 'sms' or 'email')
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
        }
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_endpoint_request_otp_credentials(self):
        endpoint = '/users/request_otp/'
        # No method specified (should be 'sms' or 'email')
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
        }
        # Bad password or username
        data['method'] = 'sms'
        data['password'] = Test.password + 'asdf'
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data['password'] = Test.password
        data['identifier'] = Test.user.username + 'asdf'
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_endpoint_request_otp_no_configs_for_method(self):
        endpoint = '/users/request_otp/'
        # No method specified (should be 'sms' or 'email')
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
        }
        data['method'] = 'sms'
        data['identifier'] = Test.user.username
        data['password'] = Test.password
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data['method'] = 'email'
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_endpoint_admin_request_otp_sms_but_no_phone(self):
        endpoint = '/users/request_otp/'
        seeds, otps = self.generate_seeds_otps_sets()
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.SMS,
            seed=seeds['sms'])
        data = {
            'method': 'sms',
            'identifier': Test.user.username,
            'password': Test.password,
        }
        Test.user.phone = None
        Test.user.save()
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        Test.user.phone = ''
        Test.user.save()
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        Test.user.phone = ' '
        Test.user.save()
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_endpoint_admin_request_otp_successful_send_otp_sms_and_email(self):
        endpoint = '/users/request_otp/'
        seeds, otps = self.generate_seeds_otps_sets()
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.SMS,
            seed=seeds['sms'])
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.EMAIL,
            seed=seeds['email'])
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.AUTHENTICATOR,
            seed=seeds['authenticator'])
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
        }
        data['method'] = 'sms'
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data['method'] = 'email'
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_login_blank_or_missing_otp(self):
        endpoint = '/users/login/'
        seeds, otps = self.generate_seeds_otps_sets()
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.AUTHENTICATOR,
            seed=seeds['authenticator'])
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
        }
        # Blank or missing otp
        for otp in ['no-key-value', '', None]:
            if otp != 'no-key-value':
                data['otp'] = otp
            response = self.client.post(endpoint, data, format='json')
            self.assertEqual(
                response.status_code,
                CustomHttpStatusCodes.HTTP_475_MFA_REQUIRED)


    def test_login_with_mfa_invalid_otp(self):
        endpoint = '/users/login/'
        seeds, otps = self.generate_seeds_otps_sets()
        invalid_otp = '111111'
        # Extremely unlikely there is a collision with the valid otps,
        # but just in case:
        while invalid_otp in otps:
            invalid_otp = random_code(length=6)
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.AUTHENTICATOR,
            seed=seeds['authenticator'])
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
            'otp': invalid_otp
        }
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(
            response.status_code,
            CustomHttpStatusCodes.HTTP_476_MFA_INVALID)


    def test_login_with_mfa_authenticator(self):
        endpoint = '/users/login/'
        seeds, otps = self.generate_seeds_otps_sets()
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.AUTHENTICATOR,
            seed=seeds['authenticator'])
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
            'otp': otps['authenticator'],
        }
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_login_with_mfa_sms(self):
        endpoint = '/users/login/'
        seeds, otps = self.generate_seeds_otps_sets()
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.SMS,
            seed=seeds['sms'])
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
            'otp': otps['sms'],
        }
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_login_with_mfa_authenticator(self):
        endpoint = '/users/login/'
        seeds, otps = self.generate_seeds_otps_sets()
        MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.EMAIL,
            seed=seeds['email'])
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
            'otp': otps['email'],
        }
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_otps_cycle_properly_on_request_otp(self):
        endpoint = '/users/request_otp/'
        seeds, otps = self.generate_seeds_otps_sets()
        sms_config = MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.SMS,
            seed=seeds['sms'])
        email_config = MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.EMAIL,
            seed=seeds['email'])
        authenticator_config = MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.AUTHENTICATOR,
            seed=seeds['authenticator'])
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
        }
        # SMS - should cycle
        seed = sms_config.seed
        data['method'] = 'sms'
        response = self.client.post(endpoint, data, format='json')
        sms_config.refresh_from_db()
        self.assertNotEqual(seed, sms_config.seed)
        # EMAIL - should cycle
        seed = email_config.seed
        data['method'] = 'email'
        response = self.client.post(endpoint, data, format='json')
        email_config.refresh_from_db()
        self.assertNotEqual(seed, email_config.seed)
        # AUTHENTICATOR - should NOT cycle
        seed = authenticator_config.seed
        data['method'] = 'email'
        response = self.client.post(endpoint, data, format='json')
        authenticator_config.refresh_from_db()
        self.assertEqual(seed, authenticator_config.seed)


    def test_otps_cycle_properly_login(self):
        endpoint = '/users/login/'
        seeds, otps = self.generate_seeds_otps_sets()
        seeds, otps = self.generate_seeds_otps_sets()
        sms_config = MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.SMS,
            seed=seeds['sms'])
        email_config = MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.EMAIL,
            seed=seeds['email'])
        authenticator_config = MFAConfig.objects.create(
            user=Test.user,
            verified=True,
            type=MFAType.AUTHENTICATOR,
            seed=seeds['authenticator'])

        # SMS - should cycle
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
            'otp': otps['sms'],
        }
        seed = sms_config.seed
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sms_config.refresh_from_db()
        self.assertNotEqual(seed, sms_config.seed)
        response = self.client.post(endpoint, data, format='json')
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)

        # EMAIL - should cycle
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
            'otp': otps['email'],
        }
        seed = email_config.seed
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        email_config.refresh_from_db()
        self.assertNotEqual(seed, email_config.seed)
        response = self.client.post(endpoint, data, format='json')
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)

        # AUTHENTICATOR - should NOT cycle
        data = {
            'identifier': Test.user.username,
            'password': Test.password,
            'otp': otps['authenticator'],
        }
        seed = authenticator_config.seed
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        authenticator_config.refresh_from_db()
        self.assertEqual(seed, authenticator_config.seed)
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
