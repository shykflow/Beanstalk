import json
import random
import urllib.parse

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from lf_service.category import LifeFrameCategoryService


from api.models import (
    AppColor,
    CategoryMapping,
)
from api.testing_overrides import LifeFrameCategoryOverrides
from lf_service.models import Category, CategoryGroup

class CategoryGetter:

    def __init__(self, cache_timeout: int|None=None, *args, **kwargs):
        self.cache_timeout = cache_timeout if cache_timeout is not None else settings.DEFAULT_CACHE_TIMEOUT

    def retrieve(self, id: int) -> Category:
        """
        Retrieves a single LifeFrame category.

        Attempts to find the category in the cache first.
        If the category is not found, uses LifeFrameCategoryService retrieve.
        """
        if settings.TESTING:
            return Category({
                'id': id,
                'name': f'category with ID {id}',
                'parent_id': None,
            })
        cache_key = f'category_{id}'
        cached_category_data = cache.get(cache_key)
        if cached_category_data is not None:
            return Category(cached_category_data)
        lf_category_service = LifeFrameCategoryService()
        category = lf_category_service.retrieve(id)
        cache.set(
            key=cache_key,
            value=category.to_dict(),
            timeout=self.cache_timeout)
        return category

    def list(self, ids: list[int]) -> tuple[list[Category], list[int]]:
        """
        Retrieves multiple LifeFrame categories.

        For each category, attempts to find it in the cache first.
        If any categories are not found in the cache, uses LifeFrameCategoryService list.
        """
        categories = []
        uncached_category_ids = []
        unknown_category_ids = []
        if settings.TESTING:
            return (
                [
                    Category({
                        'id': id,
                        'name': f'category with ID {id}',
                        'parent_id': None,
                    })
                    for id in ids
                ],
                []
            )
        for id in ids:
            cached_category_data = cache.get(f'category_{id}')
            if cached_category_data is None:
                uncached_category_ids.append(id)
                continue
            categories.append(Category(cached_category_data))
        if len(uncached_category_ids) > 0:
            lf_category_service = LifeFrameCategoryService()
            uncached_categories, unknown_category_ids = lf_category_service.list(
                uncached_category_ids)
            for uncached_category in uncached_categories:
                cache.set(
                    key=f'category_{uncached_category.id}',
                    value=uncached_category.to_dict(),
                    timeout=self.cache_timeout)
            categories += uncached_categories
        return categories, unknown_category_ids

    def popular_categories(self) -> dict[str, 'list[any]']:
        """
        Pulls popular categories from cache if it is available.
        Refreshes the cache if it needs to.
        """
        if settings.TESTING:
            return LifeFrameCategoryOverrides.popular.copy()
        categories_json = cache.get('popular_categories')
        if categories_json is None:
            call_command('cache_popular_categories')
            categories_json = cache.get('popular_categories')
        if categories_json is None:
            raise Exception('Unable to refresh popular categories')
        data: dict[str, list[dict]] = json.loads(categories_json)
        category_groups = data['category_groups']
        categories = data['categories']
        return {
            'category_groups': [CategoryGroup(data=d) for d in category_groups],
            'categories': [Category(data=d) for d in categories],
        }

    def searched_categories(
            self,
            phrase: str,
            threshold:float|None = None,
            cache_session_key: str = None) -> 'list[Category]':
        """
        Pulls searched categories from cache if it is available.
        Refreshes the cache if it needs to.

        if `cache_session_key` is set the cache lookup key will have
        `f'|{cache_session_key}'` appended.
        """
        if settings.TESTING:
            return LifeFrameCategoryOverrides.search_categories.copy()
        phrase = phrase.upper()
        url_encode_phrase = urllib.parse.quote(phrase)
        key = f'Category|search_threshold={threshold}|phrase={url_encode_phrase}'
        if cache_session_key:
            key += f'|{cache_session_key}'
        categories_json = cache.get(key)
        if categories_json is not None:
            data_dicts: list[dict] = json.loads(categories_json)
            categories: list[Category] = []
            for data in data_dicts:
                categories.append(Category(data))
            return categories
        lf_category_service = LifeFrameCategoryService()
        search_categories = lf_category_service.search(phrase, threshold=threshold)
        categories_json = json.dumps([c.to_dict() for c in search_categories])
        cache.set(
            key=key,
            value=categories_json,
            timeout=self.cache_timeout)
        return search_categories

    def relevant(self, life_frame_id: str, limit=None) -> 'dict[str, list[any]]':
        if settings.TESTING:
            return LifeFrameCategoryOverrides.relevant.copy()
        lf_category_service = LifeFrameCategoryService()
        if limit is not None:
            return lf_category_service.relevant(life_frame_id, limit)
        return lf_category_service.relevant(life_frame_id)

    def random(self, limit: int, all=False) -> 'list[Category]':
        if settings.TESTING:
            return LifeFrameCategoryOverrides.random.copy()
        lf_category_service = LifeFrameCategoryService()
        return lf_category_service.random(limit=limit, all=all)

def lf_categories_to_mappings_dict(
        lf_categories: list[Category]) -> dict[Category, CategoryMapping]:
    lf_category_ids = [c.id for c in lf_categories]
    known_mappings_qs = CategoryMapping.objects \
        .filter(category_id__in=lf_category_ids)
    known_mappings = list(known_mappings_qs)
    known_mapped_lf_category_ids = [int(m.category_id) for m in known_mappings]
    mappings: dict[Category, CategoryMapping] = {}
    for category in lf_categories:
        mapping: CategoryMapping = None
        if int(category.id) in known_mapped_lf_category_ids:
            for cm in known_mappings:
                if cm.category_id == int(category.id):
                    mapping = cm
        if mapping == None:
            mapping = CategoryMapping()
            mapping.category_id = category.id
            mapping.show_in_picker = False
        app_colors: list[str] | None = None
        if mapping.background_color is None or mapping.background_color.strip() == '':
            if app_colors is None:
                app_colors = AppColor.objects.values_list('color', flat=True)
            if len(app_colors) > 0:
                mapping.background_color = random.choice(app_colors)
            else:
                mapping.background_color = '#333333'
        mapping.name = category.name
        mapping.parent_name = category.parent_name
        mapping.parent_id = category.parent_id
        mappings[category] = mapping
    return mappings
