from .settings import *

_KILOBYTES = 1024
_MEGABYTES = 1024 * 1024

SOUTH_TESTS_MIGRATE = False

TESTING = True

TEST_RUNNER = 'api.tests.runner.TestRunner'

DEFAULT_FILE_STORAGE = 'api.testing_overrides.TestingFileSystemStorage'

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Way bigger than normal intervals to mitigate false-negative failures
OTP_TIMEOUTS = {
    'sms':           { 'interval': 60 * 60 * 5, 'label': '5 hours' },
    'email':         { 'interval': 60 * 60 * 5, 'label': '5 hours' },
    'authenticator': { 'interval': 60 * 60 * 5, 'label': '5 hours' },
}

# ffprobe log levels:
# MUST BE A STRING
#   -8: silent no matter what
#   0:  panic
#   8:  fatal
#   16: error
#   24: warning
#   32: info
#   40: info with even more info
#   48: debug
#   56: trace
FFPROBE_LOG_LEVEL='8'

FILE_UPLOADS = {
    'ATTACHMENTS': {
        'MAX_ATTACHMENTS_ALLOWED': 10,
        'MAX_FILE_SIZE': _MEGABYTES * 4,
        'MAX_THUMB_FILE_SIZE': _KILOBYTES * 10,
        'MAX_IMAGE_COMPRESS_DIMENSION': {
            'GIF': 20,
            'IMAGE': 2,
        },
        'THUMBNAIL_COMPRESS_TO_DIMENSION': {
            'IMAGE': 40,
        },
    },
    'HIGHLIGHT_IMAGE_THUMBNAIL_MAX_DIMENSION': 20,
    'IMAGE_DIMENSION': 20,
    'MAX_IMAGE_SIZE_BYTES': _MEGABYTES * 2,
    'PROFILE_PICTURE_MAX_DIMENSION': 20,
    'PROFILE_PICTURE_THUMBNAIL_MAX_DIMENSION': 20,
    'VIDEO_DIMENSION': 1920,
    'MAX_VIDEO_DURATION_SECONDS': 180, # 3 minutes
    'MAX_VIDEO_SIZE_BYTES': _MEGABYTES * 128,
    'ALLOWED_CONTENT_ASPECT_RATIOS': (4/3, 1.0, 3/4),
}

SPOOLS_CATEGORY_ARCHIVE_SLEEP_TIME = 0

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://{env.get("REDIS_HOST")}:{env.get("REDIS_PORT")}',
        "KEY_PREFIX": "test_cache",
    },
}
DISCOVER_QUERY_LIMITS['CATEGORIES_ONLY'] = False
