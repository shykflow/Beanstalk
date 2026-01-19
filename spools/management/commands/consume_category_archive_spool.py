from time import sleep
import logging
from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import (
    Experience,
)
from api.utils.categories import CategoryContentQuerysets

from spools.models import (
    CategoryArchiveSpool,
)

logger = logging.getLogger('app')

class Command(BaseCommand):
    def handle(self, *args, **options):
        if not settings.TESTING:
            logger.info('Running python manage.py consume_category_archive_spool')
        sleep_time: float = settings.SPOOLS_CATEGORY_ARCHIVE_SLEEP_TIME
        archived_spool = CategoryArchiveSpool.objects.all()
        for archived in archived_spool:
            try:
                category_id = archived.category_id
                change_to = archived.change_to
                experience_qs = CategoryContentQuerysets \
                    .experiences_qs(category_id) \
                    .filter(categories__isnull=False)
                experience_count = experience_qs.count()
                experience: Experience
                for experience in experience_qs:
                    categories: list[int] = experience.categories
                    if change_to is None:
                        categories.remove(category_id)
                    else:
                        index = categories.index(category_id)
                        categories[index] = change_to
                    experience.categories = categories
                    # Not bulk saving, this triggers a call to LifeFrame
                    # if it is the final experience to lose this category.
                    experience.save()
                    if sleep_time > 0:
                        sleep(sleep_time)
                archived.delete()
                if not settings.TESTING:
                    msg = (
                        f'Category Archive:\n'
                        f'  Experience Count: {experience_count}\n'
                        f'  Category ID: {archived.category_id}\n'
                        f'  Change To: {archived.change_to}'
                    )
                    logger.info(msg)
            except:
                if not settings.TESTING:
                    msg = (
                        f'Category Archive: Spool Error\n'
                        f'  ID: {archived.id}\n'
                        f'  Category ID: {archived.category_id}\n'
                        f'  Change To: {archived.change_to}'
                    )
                    logger.error(msg)
