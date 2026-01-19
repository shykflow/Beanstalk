import json

from api.models import User
from api.utils.life_frame_category import CategoryGetter
from lf_service.category import (
    Category,
    CategoryGroup,
)
from .continuation import Continuation


class ForYouFeedContinuation(Continuation):
    def __init__(self, user: User, token: str | None):
        self.cache_key = f'for_you_feed_{token}'
        self.user = user
        self.relevant_category_groups: list[CategoryGroup]
        self.relevant_categories: list[Category]
        self.sent_categories: list[int]
        _data_json = self.get_cache()
        _data_dict = None
        if _data_json is not None:
            _data_dict = json.loads(_data_json)
            self.relevant_categories = [
                Category(c_dict)
                for c_dict in _data_dict['relevant_categories']]
            self.relevant_category_groups = [
                CategoryGroup(cg_dict)
                for cg_dict in _data_dict['relevant_category_groups']]
            self.sent_categories = _data_dict.get('sent_categories', [])
        else:
            self.sent_categories = []
            self.relevant_category_groups = []
            self.relevant_categories = []
        super().__init__(token, _data_dict)

    def set_cache(self):
        _data_dict = {
            'relevant_categories': [
                c.to_dict()
                for c in self.relevant_categories],
            'relevant_category_groups': [
                cg.to_dict()
                for cg in self.relevant_category_groups],
            'sent_categories': self.sent_categories,
        }
        super().set_cache(_data_dict)

    def debug_print(self):
        _header = '  DiscoverContinuation('
        _additional_lines = [
            f'    relevant_categories: [{", ".join(map(str, self.relevant_categories))}],',
            f'    relevant_category_groups: [{", ".join(map(str, self.relevant_category_groups))}],',
            f'    sent_categories: [{", ".join(map(str, self.sent_categories))}]'
        ]
        super().debug_print(_header, _additional_lines)



class ForYouCategories:
    def __init__(self):
        self._relevant: list[Category] = []
        self._popular: list[Category] = []
        self._relevant_or_popular: list[Category] = []

        self._relevant_cgs: list[CategoryGroup] = []
        self._popular_cgs: list[CategoryGroup] = []
        self._relevant_or_popular_cgs: list[CategoryGroup] = []

    @property
    def relevant(self):
        return self._relevant

    @property
    def popular(self):
        return self._popular

    @property
    def relevant_or_popular(self):
        return self._relevant_or_popular

    @property
    def relevant_cgs(self):
        return self._relevant_cgs

    @property
    def popular_cgs(self):
        return self._popular_cgs

    @property
    def relevant_or_popular_cgs(self):
        return self._relevant_or_popular_cgs

    def set_relevant(self, categories: list[Category]):
        self._relevant = list(set(categories))
        self._relevant_or_popular = self._popular + self._relevant
        self._remove_duplicate_categories()

    def set_popular(self, categories: list[Category]):
        self._popular = list(set(categories))
        self._relevant_or_popular = self._popular + self._relevant
        self._remove_duplicate_categories()


    def set_relevant_cgs(self, cgs: list[CategoryGroup]):
        self.relevant_category_groups = cgs
        self._relevant_or_popular_cgs = self._relevant_cgs + self._popular_cgs
        self._remove_duplicate_category_groups()

    def set_popular_cgs(self, cgs: list[CategoryGroup]):
        self.popular_category_groups = cgs
        self._relevant_or_popular_cgs = self._relevant_cgs + self._popular_cgs
        self._remove_duplicate_category_groups()

    def _remove_duplicate_categories(self):
        new_list: list[Category] = []
        for next in self._relevant + self._popular:
            insert = True
            for i in range(len(new_list)):
                old_item = new_list[i]
                if next.id == old_item.id:
                    insert = False
                    if (next.relevant_weight or 0) > (old_item.relevant_weight or 0):
                        new_list[i] = next
            if insert:
                new_list.append(next)
        self._relevant_or_popular = new_list

    def _remove_duplicate_category_groups(self):
        new_list: list[CategoryGroup] = []
        for next in self._relevant_cgs + self._popular_cgs:
            insert = True
            for i in range(len(new_list)):
                old_item = new_list[i]
                if next.categories == old_item.categories:
                    insert = False
            if insert:
                new_list.append(next)
        self._relevant_or_popular_cgs = new_list

    def debug_print(self):
        print('ForYouCategories:')
        print(f'  relevant:                {len(self.relevant)}')
        print(f'  popular:                 {len(self.popular)}')
        print(f'  relevant_or_popular:     {len(self.relevant_or_popular)}')
        print(f'  relevant_cgs:            {len(self.relevant_cgs)}')
        print(f'  popular_cgs:             {len(self.popular_cgs)}')
        print(f'  relevant_or_popular_cgs: {len(self.relevant_or_popular_cgs)}')
