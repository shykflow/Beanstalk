import os
from pathlib import Path
from django.utils import timezone
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path('.env'))
env = os.environ

_KILOBYTES = 1024
_MEGABYTES = 1024 * 1024

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.get('DJANGO_SECRET_KEY', 'django-insecure-secret')

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = env.get('DJANGO_DEBUG') == 'true'
DEBUG = True
EARLIEST_SUPPORTED_APP_VERSION = int(env.get('EARLIEST_SUPPORTED_APP_VERSION', '0'))
LIFEFRAME_WEBHOOK_KEY = env.get('LIFEFRAME_WEBHOOK_KEY')

# Gets overridden in test_settings.py while running tests
TESTING = False

ALLOWED_HOSTS = ['*']
# ALLOWED_HOSTS = _ALLOWED_HOSTS.split(',')
# if len(ALLOWED_HOSTS) == 0:
#     exit(1)

ANYMAIL = {
    "MAILGUN_SENDER_DOMAIN": 'thebeanstalkapp.com',
}

OTP_TIMEOUTS = {
    'sms':           { 'interval': 60 * 5, 'label': '5 minutes' },
    'email':         { 'interval': 60 * 5, 'label': '5 minutes' },
    'authenticator': { 'interval': 30,     'label': '30 seconds' },
}
DISCOVER_QUERY_LIMITS = {
    'CATEGORIES_ONLY': env.get('BEANSTALK_DISCOVER_QUERY_CATEGORIES_ONLY', 'true') == 'true',
    'EXPERIENCES': int(env.get('BEANSTALK_DISCOVER_QUERY_LIMIT_EXPERIENCES', '2')),
    'PLAYLISTS': int(env.get('BEANSTALK_DISCOVER_QUERY_LIMIT_PLAYLISTS', '2')),
    'POSTS': int(env.get('BEANSTALK_DISCOVER_QUERY_LIMIT_POSTS', '2')),
    'CATEGORIES': int(env.get('BEANSTALK_DISCOVER_QUERY_LIMIT_CATEGORIES', '30')),
}
FOR_YOU_QUERY_LIMITS = {
    'NUM_SAMPLE_COMMENTS': int(env.get('BEANSTALK_FOR_YOU_NUM_SAMPLE_COMMENTS', '0')),
    'EXPERIENCES': int(env.get('BEANSTALK_FOR_YOU_QUERY_LIMIT_EXPERIENCES', '13')),
    'PLAYLISTS': int(env.get('BEANSTALK_FOR_YOU_QUERY_LIMIT_PLAYLISTS', '13')),
    'POSTS': int(env.get('BEANSTALK_FOR_YOU_QUERY_LIMIT_POSTS', '13')),
}

BEANSTALK_ADMIN_PANEL_BYPASS_AUTHENTICATOR_CHECK = env.get(
    'BEANSTALK_ADMIN_PANEL_BYPASS_AUTHENTICATOR_CHECK',
    'true').strip() == 'true'
BEANSTALK_AUTHENTICATOR_LABEL = env.get('BEANSTALK_AUTHENTICATOR_LABEL', 'BEANSTALK')

_EMAIL_BACKEND = env.get('EMAIL_BACKEND')
if _EMAIL_BACKEND == 'file':
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
elif _EMAIL_BACKEND == 'console':
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
elif _EMAIL_BACKEND == 'mailgun':
    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
    ANYMAIL["MAILGUN_API_KEY"] = env.get('MAILGUN_SECRET_KEY', 'NO_KEY_GIVEN')
else:
    raise Exception("Must provide EMAIL_BACKEND environment variable")
EMAIL_FILE_PATH = os.path.join(BASE_DIR, "email_output")

EMAIL_VERIFICATION_TIMEOUT = 900 # 15 minutes in seconds
RESEND_EMAIL_TIMEOUT = 90

AWS_ACCESS_KEY_ID = env.get('BEANSTALK_AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env.get('BEANSTALK_AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env.get('BEANSTALK_AWS_STORAGE_BUCKET_NAME')
AWS_QUERYSTRING_EXPIRE = '604800'

FACEBOOK_APP_ID = env.get('FACEBOOK_APP_ID', '').strip()
FACEBOOK_APP_SECRET = env.get('FACEBOOK_APP_SECRET', '').strip()
FACEBOOK_LOGIN_ENABLED = env.get('FACEBOOK_LOGIN_ENABLED', 'false').strip() == 'true'

TWILIO_ENABLE_TWO_FACTOR = env.get('TWILIO_ENABLE_TWO_FACTOR') == 'true'
TWILIO_SID = env.get('TWILIO_SID')
TWILIO_AUTH_TOKEN = env.get('TWILIO_AUTH_TOKEN')
TWILIO_SMS_FROM_PHONE = env.get('TWILIO_SMS_FROM_PHONE')
TWILIO_KEY = env.get('TWILIO_KEY')
TWILIO_SECRET = env.get('TWILIO_SECRET')

SENDBIRD_ENABLE_MESSAGING = env.get('SENDBIRD_ENABLE_MESSAGING') == 'true'
SENDBIRD_APPLICATION_ID = env.get('SENDBIRD_APPLICATION_ID')
SENDBIRD_API_TOKEN = env.get('SENDBIRD_API_TOKEN')
SENDBIRD_TESTING_API_TOKEN= env.get('SENDBIRD_TESTING_API_TOKEN')
SENDBIRD_TESTING_APPLICATION_ID= env.get('SENDBIRD_TESTING_APPLICATION_ID')

STALE_DEVICE_THRESHOLD=timezone.timedelta(days=30*3)

SKIP_MARK_FOLLOW_FEED_SEEN=env.get('BEANSTALK_SKIP_MARK_FOLLOW_FEED_SEEN', 'false') == 'true'

DEFAULT_FILE_STORAGE = env.get('FILE_STORAGE', 'storages.backends.s3boto3.S3Boto3Storage')

# User all lower case
ALLOWED_MIME_TYPES = {
    'application' : (
        'pdf',
        # .doc
        'msword',
        'cdfv2',
        # .docx files are zips
        # 'zip',
        # .docx
        'vnd.openxmlformats-officedocument.wordprocessingml.document',
    ),
    'audio': (
        'mpeg', # mp3
    ),
    'image': (
        'avif',
        'bmp',
        'gif',
        'jpg',
        'jpeg',
        'png',
        'webp',
        # Apple image types
        'heic',
        'heif',
    ),
    'video': (
        '3gpp',      # .3gp files
        '3gpp2',     # .3g2 files
        'mp4',       # .m4v and .mp4 files
        'quicktime', # .mov and .qt files
        'webm',
        'x-msvideo', # .avi files
    ),
    'text': (
        'plain',
    ),
}
# It's ok if the flutter app reads jpeg but python reads jpg.
MIME_TYPE_EQUIVALENTS = {
    'jpeg': (
        'image/jpg',
        'image/jpeg',
    ),
    'msword': (
        'application/cdfv2',
        'application/msword',
        'application/x-ole-storage',
    )
}

# https://www.ibm.com/support/pages/what-magic-number
MAGIC_CHUNK_SIZE = 2048

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
FFPROBE_LOG_LEVEL = '16'

FILE_UPLOADS = {
    'ATTACHMENTS': {
        'MAX_ATTACHMENTS_ALLOWED': 10,
        'MAX_FILE_SIZE': _MEGABYTES * 8,
        'MAX_THUMB_FILE_SIZE': _KILOBYTES * 10,
        'MAX_IMAGE_COMPRESS_DIMENSION': {
            'GIF': 320,
            'IMAGE': 1920,
        },
        'THUMBNAIL_COMPRESS_TO_DIMENSION': {
            'IMAGE': 240,
        },
    },
    'HIGHLIGHT_IMAGES': {
        'MAX_FILE_SIZE': _MEGABYTES * 2,
        'MAX_THUMBNAIL_FILE_SIZE': _KILOBYTES * 10,
        'COMPRESS_DIMENSION': 1920,
        'THUMBNAIL_COMPRESS_DIMENSION': 240,
    },
    'HIGHLIGHT_IMAGE_THUMBNAIL_MAX_DIMENSION': 256,
    'IMAGE_DIMENSION': 1920,
    'MAX_IMAGE_SIZE_BYTES': _MEGABYTES * 2,
    'PROFILE_PICTURE_MAX_DIMENSION': 200,
    'PROFILE_PICTURE_THUMBNAIL_MAX_DIMENSION': 64,
    'VIDEO_DIMENSION': 1920,
    'MAX_VIDEO_DURATION_SECONDS': 180, # 3 minutes
    'MAX_VIDEO_SIZE_BYTES': _MEGABYTES * 128,
    'ALLOWED_CONTENT_ASPECT_RATIOS': (4/3, 1.0, 3/4),
}

# Application definition
INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',

    # Third Party
    'channels',
    'django_extensions',
    'django_filters',
    'rest_framework',
    'rest_framework.authtoken',
    'django_admin_inline_paginator',
    'django_cleanup.apps.CleanupConfig',
    'storages',
    'anymail',
    "django_celery_beat",
    #'drf_yasg',
    # Beanstalk
    'api',
    'lf_service',
    'schedules',
    'sponsorship',
    'spools',
]

AUTH_USER_MODEL = 'api.User'

CSRF_TRUSTED_ORIGINS = []
_CSRF_TRUSTED_ORIGINS = env.get('BEANSTALK_CSRF_TRUSTED_ORIGINS')
if _CSRF_TRUSTED_ORIGINS is not None:
    _CSRF_TRUSTED_ORIGINS = _CSRF_TRUSTED_ORIGINS.strip()
    CSRF_TRUSTED_ORIGINS = _CSRF_TRUSTED_ORIGINS.split(',')
SECURE_CROSS_ORIGIN_OPENER_POLICY = None
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'beanstalk.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, "templates"),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'libraries': {
                'api_templatetags': 'api.templatetags',
            }
        },
    },
]

WSGI_APPLICATION = 'beanstalk.wsgi.application'
ASGI_APPLICATION = 'beanstalk.asgi.application'

ADMIN_URL = env.get('ADMIN_URL')

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    'default': {
        # 'ENGINE': 'django.db.backends.postgresql',
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'HOST':     env.get('BEANSTALK_DB_HOST'),
        'PORT':     5432,
        'NAME':     env.get('BEANSTALK_DB_DATABASE_NAME'),
        'USER':     env.get('BEANSTALK_DB_USER'),
        'PASSWORD': env.get('BEANSTALK_DB_PASSWORD'),
    }
}

DEFAULT_CACHE_TIMEOUT = 900 # 15 minutes in seconds

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://{env.get("REDIS_HOST")}:{env.get("REDIS_PORT")}',
    },
}

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'api.validators.PasswordNumberValidator',
    },
    {
        'NAME': 'api.validators.PasswordLetterCaseValidator',
    },
    {
        'NAME': 'api.validators.PasswordSymbolValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
]

LOG_LEVEL = env.get('LOG_LEVEL', 'WARNING')
LOGGING = {
     'version': 1,
     'disable_existing_loggers': False,
     'filters': {
         'require_debug_false': {
             '()': 'django.utils.log.RequireDebugFalse'
         }
     },
     'handlers': {
         'file': {
             'level': LOG_LEVEL,
             'class': 'logging.FileHandler',
             'filename': env.get('LOG_FILE', '/var/log/django.log'),
         },
         'mail_admins': {
             'level': LOG_LEVEL,
             'filters': ['require_debug_false'],
             # https://docs.djangoproject.com/en/4.0/topics/logging/#adminemailhandler
             'class': 'django.utils.log.AdminEmailHandler'
         },
         'console': {
             'level': LOG_LEVEL,
             'class': 'logging.StreamHandler',
         }
     },
     'loggers': {
         'django.request': {
             'handlers': ['console'],
             'level': LOG_LEVEL,
             'propagate': True,
             'formatter': 'verbose',
         },
         'django.db.backends': {
             'handlers': ['console'],
             'level': 'DEBUG'
         },
         'app': {
             'handlers': ['console'],
             'level': LOG_LEVEL,
             'formatter': 'simple',
         },
         'app_verbose': {
             'handlers': ['console'],
             'level': LOG_LEVEL,
             'formatter': 'verbose',
         },
     },
     'formatters': {
         'verbose': {
             'format': '{name} {levelname} {asctime} {module} {process:d} {thread:d} {message}',
             'style': '{',
         },
         'simple': {
             'format': '{levelname} {message}',
             'style': '{',
         },
     },
 }


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = 'static'
STATICFILES_DIRS = [
    ('beanstalk', '/app/beanstalk/static/'),
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'api.utils.token_authentication.BearerTokenAuthentication',
        # "rest_framework.authentication.SessionAuthentication",
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        'api.utils.permissions.IsVerifiedPermission'
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.TemplateHTMLRenderer',
    ),
}

MAX_PAGINATION_PAGE_SIZE = 50

SPOOLS_CATEGORY_ARCHIVE_SLEEP_TIME = 0.25

#CELERY_BROKER_URL = 'amqp://guest:guest@rabbitmq:5672//'
#CELERY_RESULT_BACKEND = 'rpc://'
#CELERY_ACCEPT_CONTENT = ['json']
#CELERY_TASK_SERIALIZER = 'json'
#CELERY_RESULT_SERIALIZER = 'json'
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_BACKEND = 'redis://redis:6379/0'
CELERY_TASK_TRACK_STARTED = True
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_FORCE_FORKED = True
