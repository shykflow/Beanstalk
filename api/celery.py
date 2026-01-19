
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beanstalk.settings')

app = Celery('beanstalk')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'delete-custom-categories': {
        'task': 'api.tasks.delete_custom_categories',
        'schedule': crontab(hour=0, minute=0)
    }
}
app.conf.broker_connection_retry_on_startup = True

