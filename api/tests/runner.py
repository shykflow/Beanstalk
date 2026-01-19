import shutil
import os

from django.conf import settings
from django.test.runner import DiscoverRunner
from unittest.mock import patch

from api.testing_overrides import (
    GlobalTestCredentials,
    MockTwilioMessageInstance,
    LifeFrameCategoryOverrides,
)

class UnitTestPatches:
    def __init__(self):
        self.send_sms = patch(
            'api.utils.twilio_messaging.TwilioMessaging.send_sms',
            return_value=MockTwilioMessageInstance())
        self.send_email = patch(
            'django.core.mail.EmailMultiAlternatives.send',
            return_value=0)
        self.send_fcm_message = patch(
            'firebase_admin.messaging.send',
            return_value=0)

    def start(self):
        self.mock_send_sms = self.send_sms.start()
        self.mock_send_email = self.send_email.start()
        self.mock_send_fcm_message = self.send_fcm_message.start()

    def stop(self):
        self.send_sms.stop()
        self.send_email.stop()
        self.send_fcm_message.stop()

class MixinRunner(object):

    unit_test_patches: UnitTestPatches

    def setup_databases(self, *args, **kwargs):
        # Pre test database create
        self.unit_test_patches = UnitTestPatches()
        self.unit_test_patches.start()
        setup_db_super = super(MixinRunner, self).setup_databases(*args, **kwargs)
        GlobalTestCredentials.initialize()
        LifeFrameCategoryOverrides.set_cache()
        return setup_db_super

    def teardown_databases(self, *args, **kwargs):
        # Pre test database teardown
        teardown_db_super = super(MixinRunner, self).teardown_databases(*args, **kwargs)

        # Post test database teardown
        self.unit_test_patches.stop()
        temp_test_files_dir = f'{settings.BASE_DIR}/api/tests/tmp'
        if os.path.isdir(temp_test_files_dir):
            shutil.rmtree(temp_test_files_dir)

        return teardown_db_super

class TestRunner(MixinRunner, DiscoverRunner):
    pass
