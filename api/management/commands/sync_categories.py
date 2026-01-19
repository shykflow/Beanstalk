from django.core.management.base import BaseCommand
import logging
import uuid

from api.models import CustomCategory, Experience
from api.utils.life_frame_category import CategoryGetter

logger = logging.getLogger('app')

class Command(BaseCommand):

    category_getter = CategoryGetter()
    cache_key = uuid.uuid4()

    def handle(self, *args, **kwargs):
        logger.info('Synchronizing categories')
        custom_categories = CustomCategory.objects \
            .filter(needs_manual_review=False)
        if not custom_categories.exists():
            logger.info('  No custom categories found')
            return

        for category in custom_categories:
            category_name = category.name
            logger.info(f'  custom category: {category_name}')
            lf_categories = Command.category_getter.searched_categories(
                phrase=category_name,
                threshold=0.9,
                cache_session_key=Command.cache_key)
            if len(lf_categories) == 0:
                continue
            if len(lf_categories) > 1:
                category.needs_manual_review = True
                category.save()
                continue
            lf_category = lf_categories[0]
            logger.info(f'Removing {category_name} setting {lf_category.id}')
            experiences = Experience.objects.filter(custom_categories=category)
            for experience in experiences:
                experience.custom_categories.remove(category)
                experience.categories.append(lf_category.id)
                experience.save()
            category.delete()
