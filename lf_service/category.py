import requests

from . import (
    LifeFrameService,
    LifeFrameUserIDRequiredError,
    LifeFrameException,
)
from .models import (
    Category,
    CategoryGroup,
)

class LifeFrameCategoryService(LifeFrameService):

    log_label = 'LifeFrameCategoryService'

    def retrieve(self, id: int) -> Category:
        url = ''.join([
            self.api_url,
            f'/categories/{id}/',
        ])
        self._log(f"GET {url}")
        response = requests.get(url, headers=self._headers())
        self._check_for_forbidden(response)
        if not (200 <= response.status_code < 300):
            raise LifeFrameException(response=response)
        data = response.json()
        return Category(data)


    def list(self, ids: list[int]) -> tuple[list[Category], list[int]]:
        """
        returns a tuple:
        First return value:
            list[Category]
            The list of categories asked for
        Second return value:
            list[int]
            not found ids
        """
        if len(ids) == 0:
            return ([], [])
        query_params = {
            'ids': ",".join(map(str, ids))
        }
        url = ''.join([
            self.api_url,
            '/categories/',
            self.params_to_url_part(query_params),
        ])
        self._log(f"GET {url}")
        response = requests.get(url, headers=self._headers())
        self._check_for_forbidden(response)
        if not (200 <= response.status_code < 300):
            raise LifeFrameException(response=response)
        data = response.json()
        category_dicts = data.get('categories', [])
        categories = [Category(d) for d in category_dicts]
        unknown_ids = data.get('unknown_ids', [])
        return categories, unknown_ids


    def popular(self,
            limit: int=10,
            org_activities_only: bool=True) -> 'list[Category]':
        query_params = {
            'limit': str(limit),
            'org_activities_only': 'true' if org_activities_only else 'false',
            'version': '2',
        }
        url = ''.join([
            self.api_url,
            '/categories/popular/',
            self.params_to_url_part(query_params),
        ])
        self._log(f"GET {url}")
        response = requests.get(url, headers=self._headers())
        self._check_for_forbidden(response)
        if not (200 <= response.status_code < 300):
            raise LifeFrameException(response=response)
        data = response.json()
        return {
            'category_groups': [
                CategoryGroup(d)
                for d in data['category_groups']
            ],
            'categories': [
                Category(d)
                for d in data['categories']
            ],
        }


    def relevant(self,
            life_frame_id: str,
            limit: int=10) -> 'dict[str, list[any]]':
        if life_frame_id is None:
            raise LifeFrameUserIDRequiredError()
        query_params = {
            'user': life_frame_id,
            'limit': str(limit),
            'version': '2',
        }
        url = ''.join([
            self.api_url,
            '/categories/relevant/',
            self.params_to_url_part(query_params),
        ])
        self._log(f"GET {url}")
        response = requests.get(url, headers=self._headers())
        self._check_for_forbidden(response)
        if not (200 <= response.status_code < 300):
            raise LifeFrameException(response=response)
        data = response.json()
        return {
            'category_groups': [
                CategoryGroup(d)
                for d in data['category_groups']
            ],
            'categories': [
                Category(d)
                for d in data['categories']
            ],
        }


    def random(self, limit: int, all=False) -> 'list[Category]':
        url = f'{self.api_url}/categories/random/'
        query_params = {
            'limit': str(limit),
        }
        query_params['all'] = 'true' if all else 'false'
        url = ''.join([
            self.api_url,
            '/categories/random/',
            self.params_to_url_part(query_params),
        ])
        self._log(f"GET {url}")
        response = requests.get(url, headers=self._headers())
        self._check_for_forbidden(response)
        if not (200 <= response.status_code < 300):
            raise LifeFrameException(response=response)
        data = response.json()
        return [Category(d) for d in data]


    def search(self,
            phrase: str,
            content_categories_only: bool | None = None,
            threshold: float | None = None) -> 'list[Category]':
        if phrase is None or phrase.strip() == '':
            raise LifeFrameException(message='Category search requires a phrase')
        url = f'{self.api_url}/categories/search/'
        query_params = {
            'phrase': phrase,
        }
        if content_categories_only is not None:
            query_params['content_categories_only'] =\
                str(content_categories_only).lower()
        if threshold is not None:
            query_params['threshold'] = str(threshold)
        url = ''.join([
            self.api_url,
            '/categories/search/',
            self.params_to_url_part(query_params)
        ])
        self._log(f"GET {url}")
        response = requests.get(url, headers=self._headers())
        self._check_for_forbidden(response)
        if not (200 <= response.status_code < 300):
            raise LifeFrameException(
                response=response,
                message=f'Could not search "{phrase}"')
        data = response.json()
        return [Category(d) for d in data]


    def record_activity(
        self, lifeframe_id: int, categories: 'list[int]') -> requests.Response:
        url = ''.join([
            self.api_url,
            f'/users/{lifeframe_id}/record_activity/',
        ])
        self._log(f"POST {url}")
        data = {
            'influenced_by': None,
            'categories': categories,
            'action_type': 1,
            'weight': 1,
        }
        response = requests.post(url, headers=self._headers(), json=data)
        self._check_for_forbidden(response)
        if not (200 <= response.status_code < 300):
            raise LifeFrameException(response=response)
        return response


    def mark_has_content(self, category_ids: 'list[int]') -> requests.Response:
        url = ''.join([
            self.api_url,
            '/categories/mark_has_content/',
        ])
        self._log(f"POST {url}")
        data = {
            "categories": category_ids,
        }
        response = requests.post(url, headers=self._headers(), json=data)
        self._check_for_forbidden(response)
        if not (200 <= response.status_code < 300):
            raise LifeFrameException(response=response)
        return response


    def mark_has_no_content(self, category_ids: 'list[int]') -> requests.Response:
        url = ''.join([
            self.api_url,
            '/categories/mark_has_no_content/',
        ])
        self._log(f"POST {url}")
        data = {
            "categories": category_ids,
        }
        response = requests.post(url, headers=self._headers(), json=data)
        self._check_for_forbidden(response)
        if not (200 <= response.status_code < 300):
            raise LifeFrameException(response=response)
        return response
