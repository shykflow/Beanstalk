from datetime import timedelta
import json
import logging
import requests

from django.core.management.base import BaseCommand
from django.core.cache import cache

from lf_service.models import Category, CategoryGroup
from lf_service.category import LifeFrameCategoryService

logger = logging.getLogger('app')

class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info('Running python manage.py cache_popular_categories')
        cache_lifetime = int(timedelta(days=1).total_seconds())
        lf_category_service = LifeFrameCategoryService()

        try:
            intended_category_count = 100
            response = lf_category_service \
                .popular(limit=intended_category_count)
            category_groups: list[CategoryGroup] = response['category_groups']
            categories: list[Category] = response['categories']
            popular_categories_count = len(categories)
            logger.info(f'popular_categories_count: {popular_categories_count}')
            data = {
                'category_groups': [c.to_dict() for c in category_groups],
                'categories': [c.to_dict() for c in categories],
            }
            logger.info(f'number of categories being cached as "popular": {len(data)}')
            categories_json = json.dumps(data)
            cache.set(
                key='popular_categories',
                value=categories_json,
                timeout=cache_lifetime)
        except requests.exceptions.ConnectionError:
            logger.info('Count not communicate with LifeFrame')
        except Exception as e:
            logger.info(str(e))
