import os

from django.apps import AppConfig
from django.contrib import admin

from beanstalk.config_validations import (
    AWSS3BucketValidation,
    AWSKeysValidation,
    PostgresValidation,
    LifeFrameAPIValidation,
    FirebaseValidation,
    MailgunValidation,
    SendbirdKeysValidation,
    TwilioKeysValidation,
    # FailValidation,
)


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        admin.site.site_header = "Beanstalk Admin"

        # Import signals so they're loaded at runtime
        import api.signals

        config_validations = [
            AWSS3BucketValidation(),
            AWSKeysValidation(),
            PostgresValidation(),
            LifeFrameAPIValidation(),
            FirebaseValidation(),
            MailgunValidation(),
            TwilioKeysValidation(),
            SendbirdKeysValidation(),
            # FailValidation(),
        ]

        if os.environ.get('RUN_MAIN'):
            for validation in config_validations:
                error_msg = validation.test()
                if error_msg is not None:
                    new_line = "\n  "
                    msg = f'Failed Configuration Validation{new_line}{new_line.join(error_msg)}'
                    raise Exception(msg)
