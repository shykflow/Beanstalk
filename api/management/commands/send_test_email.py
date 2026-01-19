import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
# from anymail.message import attach_inline_image_file

"""
Usage:
    ./manage.py send_test_email nateb@gurutechnologies.net
    ./manage.py send_test_email nateb@gurutechnologies.net, loganp@gurutechnologies.net
"""

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('email-list', type=str)

    def handle(self, *args, **options):
        email_list_str = options.get('email-list', None)
        email_list = email_list_str.split(',')
        message_params = {
            'link': 'https://google.com'
        }
        text = render_to_string('outgoing_email_test.txt', context=message_params)
        html = render_to_string('outgoing_email_test.html', context=message_params)

        sender_domain = settings.ANYMAIL['MAILGUN_SENDER_DOMAIN']
        message = EmailMultiAlternatives(
            subject=f"This is a test email from Beanstalk",
            body=text,
            from_email=f"Example <noreply@{sender_domain}>",
            to=email_list,
            reply_to=[f"NoReply <noreply@{sender_domain}>"]
        )
        # cid = attach_inline_image_file(message, os.path.join(settings.BASE_DIR, 'static/images/logo.png'), idstring="logo")

        message.attach_alternative(html, "text/html")
        message.send()
