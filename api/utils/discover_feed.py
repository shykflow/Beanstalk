import json

from api.models import User
from lf_service.category import (
    Category,
    CategoryGroup,
)
from .continuation import Continuation

class DiscoverFeedContinuation(Continuation):
    def __init__(self, user: User, token: str | None):
        self.cache_key = f'discover_feed_{token}'
        self.user = user
        self.cached_category_groups: list[CategoryGroup]
        self.cached_categories: list[Category]
        self.popular_category_ids: list[int]
        self.page = 0
        _data_json = self.get_cache()
        _data_dict = None
        if _data_json is not None:
            _data_dict = json.loads(_data_json)
            self.page = _data_dict.get('page', 0)
            self.cached_categories = [Category(c) for c in _data_dict.get('cached_categories', [])]
            self.popular_category_ids = _data_dict.get('popular_category_ids', [])
        else:
            self.cached_categories = []
            self.cached_category_groups = []
            self.popular_category_ids = []
            self.set_cache()
        super().__init__(token, _data_dict)

    def set_cache(self):
        _data_dict = {
            'page': self.page,
            'cached_categories': [c.to_dict() for c in self.cached_categories],
            'popular_category_ids': self.popular_category_ids,
        }
        super().set_cache(_data_dict)

    def unique_cached_categories(self):
        unique_categories = []
        unique_category_ids = []
        for category in self.cached_categories:
            if category.id not in unique_category_ids:
                unique_category_ids.append(category.id)
                unique_categories.append(category)
        self.cached_categories = unique_categories

    def debug_print(self):
        _header = '  DiscoverContinuation('
        _additional_lines = [
            f'    page: {self.page}',
            f'    cached_categories: {len(self.cached_categories)}',
            f'    popular_category_ids: {len(self.popular_category_ids)}',
            # f'    cached_categories: [{", ".join([str(c.id) for c in self.cached_categories])}],',
            # f'    popular_category_ids: [{", ".join(map(str, self.popular_category_ids))}]',
        ]
        super().debug_print(_header, _additional_lines)
