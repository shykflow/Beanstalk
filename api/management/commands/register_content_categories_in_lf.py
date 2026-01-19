import logging

from django.core.management.base import BaseCommand

from lf_service.category import LifeFrameCategoryService

from api.models import Experience

logger = logging.getLogger('app')

class Command(BaseCommand):
    """
    Gathers all category IDs from all Experiences
    and tells LifeFrame about all of them
    """
    def handle(self, *args, **options):
        logger.info('register_content_categories_in_lf')
        lf_category_service = LifeFrameCategoryService()

        results_qs = Experience.objects \
            .filter(categories__isnull=False) \
            .values_list('categories', flat=True)
        results = list(results_qs)
        handled = []
        for i in range(len(results)):
            results[i] = list(set(sorted(results[i])))
        for category_ids in results:
            logger.info(f'Marking LifeFrame content categories with count: {len(category_ids)}')
            if category_ids in handled:
                logger.info('Skipping, already handled')
                continue
            try:
                lf_category_service.mark_has_content(category_ids)
                handled.append(category_ids)
            except Exception as e:
                logger.error(str(e))
