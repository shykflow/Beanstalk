import json
from django.db import connection
from django.db.models import QuerySet, Q

from api.models import (
    Experience,
    Playlist,
    Post,
)

from .continuation import Continuation


class CategoryContentContinuation(Continuation):
    def __init__(self, token: str | None):
        self.cache_key = f'category_content_{token}'
        self.sent_users: list[int]
        _data_json = self.get_cache()
        _data_dict = None if _data_json is None else json.loads(_data_json)
        if _data_json is not None:
            _data_dict = json.loads(_data_json)
            self.sent_users = _data_dict.get('sent_users', [])
        else:
            self.sent_users = []
        super().__init__(token, _data_dict)

    def debug_print(self):
        _header = '  CategoryContentContinuation('
        additional_lines = [
            f'    sent_users: [{", ".join(map(str, self.sent_users))}]'
        ]
        super().debug_print(_header, additional_lines)


class CategoryContentQuerysets:
    @staticmethod
    def experiences_qs(category_id: int) -> QuerySet[Experience]:
        return Experience.objects \
            .filter(categories__contains=[category_id])

    def playlists_qs(category_id: int) -> QuerySet[Playlist]:
        return Playlist.objects \
            .filter(aggregated_categories__contains=[category_id])

    def posts_qs(category_id: int) -> QuerySet[Post]:
        experience_q = Q(
            experience__in=CategoryContentQuerysets.experiences_qs(category_id))
        playlist_q = Q(
            playlist__in=CategoryContentQuerysets.playlists_qs(category_id))
        return Post.objects \
            .filter(experience_q | playlist_q)


def get_category_content_counts(category_ids: list[int]) -> dict[int, int]:
    with connection.cursor() as cursor:
        sql = f"""
            SELECT
                category_id, COUNT(category_id)
            FROM (
                SELECT
                    UNNEST(categories) AS category_id,
                    exp.id AS exp_id
                FROM
                    api_experience exp
            ) exp_counts
            WHERE
                category_id = ANY(%(category_ids)s)
            GROUP BY
                category_id
            ORDER BY
                category_id;
        """
        params = {
            'category_ids': category_ids,
        }
        cursor.execute(sql, params)
        category_sets = cursor.fetchall()
        category_dict = {}
        for category_set in category_sets:
            category_dict[category_set[0]] = category_set[1]
        return category_dict

