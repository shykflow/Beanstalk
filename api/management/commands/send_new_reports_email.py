from datetime import datetime
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.template.loader import render_to_string

from api.models import (
    Report,
    User,
)


logger = logging.getLogger('app')

class Command(BaseCommand):

    def handle(self, *args, **options):
        logger.info('Running python manage.py send_new_reports_email')

        admin_url: str = settings.ADMIN_URL
        if admin_url is None or admin_url.strip() == '':
            raise Exception(''.join([
                'Could not send emails:',
                'ADMIN_URL envirinment variable must be set',
            ]))

        notify_users: QuerySet[User] = User.objects \
            .filter(
                is_staff=True,
                email_verified=True,
                notify_about_new_content_reports=True) \
            .all()

        if not notify_users.exists():
            print('No users to email. ' + \
                'At least 1 user needs to be marked as ' + \
                'is_staff=True, ' + \
                'email_verified=True, ' + \
                'notify_about_new_content_reports=True')
            exit(1)

        notify_users_emails: list[str] = [u.email for u in notify_users]
        try:
            not_emailed_qs = Report.objects.filter(cron_emailed=False)
            new_reports_since_last_email_count = not_emailed_qs.count()
            if new_reports_since_last_email_count == 0:
                return

            new_reports_since_last_email = list(not_emailed_qs.all())
            unacknowledged_reports_count = Report.objects \
                .filter(acknowledged=False) \
                .count()

            now_string = datetime.now().strftime("%m%d%Y%H%M")
            html_context = {
                'new_reports_since_last_email_count': new_reports_since_last_email_count,
                'unacknowledged_reports_count': unacknowledged_reports_count,
                'admin_url': admin_url,
                'now': now_string,
            }
            text = render_to_string('nofity_about_new_reports.txt', context=html_context)
            html = render_to_string('nofity_about_new_reports.html', context=html_context)
            sender_domain = settings.ANYMAIL['MAILGUN_SENDER_DOMAIN']
            message = EmailMultiAlternatives(
                subject=f"User generated content has been reported and needs attention [{now_string}]",
                body=text,
                from_email=f"Beanstalk Cron <noreply@{sender_domain}>",
                to=notify_users_emails,
                reply_to=[f"NoReply <noreply@{sender_domain}>"])
            # cid = attach_inline_image_file(
            #   message,
            #   os.path.join(settings.BASE_DIR, 'static/images/logo.png'),
            #   idstring="logo")

            message.attach_alternative(html, "text/html")
            message.send()

            for report in new_reports_since_last_email:
                report.cron_emailed = True

            Report.objects.bulk_update(new_reports_since_last_email, ['cron_emailed'])
        except:
            raise
