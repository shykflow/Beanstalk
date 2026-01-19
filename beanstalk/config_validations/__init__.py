from abc import abstractmethod
import os

env = os.environ


class Validation():
    @abstractmethod
    def test(self) -> list[str] | None:
        pass


class AWSS3BucketValidation(Validation):
    def test(self) -> list[str] | None:
        bucket = env.get('BEANSTALK_AWS_STORAGE_BUCKET_NAME')
        if bucket is None or bucket.strip() == '':
            return ['BEANSTALK_AWS_STORAGE_BUCKET_NAME environment variable not set']
        return None



class AWSKeysValidation(Validation):
    def test(self) -> list[str] | None:
        USE_AWS_KEYS = env.get('USE_AWS_KEYS') == 'true'
        if not USE_AWS_KEYS:
            return None
        required = [
            'BEANSTALK_AWS_ACCESS_KEY_ID',
            'BEANSTALK_AWS_SECRET_ACCESS_KEY',
        ]
        for r in required:
            if env.get(r) is None:
                return [
                    f'{r} is required',
                    '  because USE_AWS_KEYS=true',
                ]
        return None


class PostgresValidation(Validation):
    def test(self) -> list[str] | None:
        required = [
            'BEANSTALK_DB_HOST',
            'BEANSTALK_DB_DATABASE_NAME',
            'BEANSTALK_DB_USER',
            'BEANSTALK_DB_PASSWORD',
        ]
        for r in required:
            if env.get(r) is None:
                return [f'{r} is required']
        return None


class MailgunValidation(Validation):
    def test(self) -> list[str] | None:
        if env.get('EMAIL_BACKEND') == 'mailgun':
            if env.get('MAILGUN_SECRET_KEY') is None:
                return ['MAILGUN_SECRET_KEY environment variable not set']
        return None


class LifeFrameAPIValidation(Validation):
    def test(self) -> list[str] | None:
        url = env.get('LIFEFRAME_API_URL')
        if url is None or url.strip() == '':
            return ['LIFEFRAME_API_URL environment variable not set']
        return None


class FirebaseValidation(Validation):
    def test(self) -> list[str] | None:
        credentials = env.get('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials is None or credentials.strip() == '':
            return ['GOOGLE_APPLICATION_CREDENTIALS environment variable not set.']
        if not os.path.exists(credentials):
            return [f'{credentials} does not point to a file']
        return None


class TwilioKeysValidation(Validation):
    def test(self) -> list[str] | None:
        TWILIO_ENABLE_TWO_FACTOR = env.get('TWILIO_ENABLE_TWO_FACTOR') == 'true'
        if not TWILIO_ENABLE_TWO_FACTOR:
            return None
        required = [
            'TWILIO_SID',
            'TWILIO_AUTH_TOKEN',
            'TWILIO_KEY',
            'TWILIO_SECRET',
        ]
        for r in required:
            if env.get(r) is None:
                return [
                    f'{r} is required',
                    '  because TWILIO_ENABLE_TWO_FACTOR=true',
                ]
        return None


class SendbirdKeysValidation(Validation):
    def test(self) -> list[str] | None:
        SENDBIRD_ENABLE_MESSAGING = env.get('SENDBIRD_ENABLE_MESSAGING') == 'true'
        if not SENDBIRD_ENABLE_MESSAGING:
            return None
        required = [
            'SENDBIRD_APPLICATION_ID',
            'SENDBIRD_API_TOKEN',
            'SENDBIRD_TESTING_API_TOKEN',
            'SENDBIRD_TESTING_APPLICATION_ID',
        ]
        for r in required:
            if env.get(r) is None:
                return [
                    f'{r} is required',
                    '  because SENDBIRD_ENABLE_MESSAGING=true',
                ]
        return None


class FailValidation(Validation):
    """For testing."""
    def test(self) -> list[str] | None:
        return ['Validation Failed']
