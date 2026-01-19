import logging

from django.core.management.base import BaseCommand

from api.services.firebase import FirebaseService

logger = logging.getLogger('app')
firebase = FirebaseService()

class Command(BaseCommand):
    def handle(self, *args, **options):
        title = input('Title: ')
        body = input('Body: ')
        confirmed = input(f'Are you sure you want to send this notification?\ntitle: {title}\nbody:{body}\n(y/N): ') == 'y'
        if not confirmed:
            return
        logger.info('Sending global notification')
        firebase.send_message_to_topic('global', title=title, body=body, data_dict={})
