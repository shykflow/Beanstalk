import logging
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from api.models import User
from api.testing_overrides import GlobalTestCredentials

class TestCaseLogLevel:
    """
    Log levels for the `SilenceableAPITestCase`.

    `ERROR` and `CRITICAL` will match the level from `logging`.
    `DISABLED` will disable all logging.
    """
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    DISABLED = 60


class SilenceableAPITestCase(APITestCase):
    """
    By default, hides all the automatic printing that happens on any non 200
    range response from testing the API.

    Use `print('some message')` instead of logging.

    A `custom_log_level` variable can be set to apply that logging level to every test case:
    ```
    from . import SilenceableAPITestCase, TestCaseLogLevel
    class Test(SilenceableAPITestCase):
        custom_log_level = TestCaseLogLevel.DISABLED
    ```
    """
    custom_log_level = TestCaseLogLevel.ERROR
    logger = logging.getLogger('django.request')
    original_log_level = logger.getEffectiveLevel()

    def setUp(self) -> None:
        """
        Ran before each test to ensure the logging is correct for the custom log level.

        Be sure to call `super().setUp()` in overrides.
        """
        if self.custom_log_level == TestCaseLogLevel.DISABLED:
            if not self.logger.disabled:
                self.logger.disabled = True
            return
        if self.logger.disabled:
            self.logger.disabled = False
        current_log_level = self.logger.getEffectiveLevel()
        if current_log_level != self.custom_log_level:
            self.logger.setLevel(self.custom_log_level)


    def tearDown(self) -> None:
        """Reset the log level back to normal"""
        current_log_level = self.logger.getEffectiveLevel()
        if current_log_level != self.original_log_level:
            self.logger.setLevel(self.original_log_level)


def disable_logging(test_case_method):
    """
    Decorator to disable logging for a single `SilenceableAPITestCase` method.

    Example:
    ```
    @disable_logging
    def test_case_name(self):
        raise Exception() # Won't log exception to console
    ```
    """
    def wrapper(cls: SilenceableAPITestCase):
        cls.logger.disabled = True
        test_case_method(cls)
        # No need to reset disabled to False since the setUp() on the next test case will do that
    return wrapper
