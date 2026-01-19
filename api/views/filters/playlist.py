from django.db.models import QuerySet
from rest_framework import filters
from rest_framework.request import Request

from api.utils import split_ints
from api.models import User

class PlaylistCreatedByFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request: Request, queryset: QuerySet, view) -> QuerySet:
        created_by = request.query_params.get('created_by')
        if created_by is not None:
            queryset = queryset.filter(created_by_id=created_by)
        return queryset

class PlaylistNotPinnedByFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request: Request, queryset: QuerySet, view) -> QuerySet:
        pinned_by = request.query_params.get('not_pinned_by')
        if pinned_by is not None:
            queryset = queryset.exclude(users_pinned__id=pinned_by)
        return queryset

class PlaylistNotCreatedByFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request: Request, queryset: QuerySet, view) -> QuerySet:
        not_created_by = request.query_params.get('not_created_by')
        if not_created_by is not None:
            queryset = queryset.exclude(created_by_id=not_created_by)
        return queryset

class PlaylistAcceptedByFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request: Request, queryset: QuerySet, view):
        _accepted_by: str = request.query_params.get('accepted_by')
        if _accepted_by is not None:
            accepted_by = int(_accepted_by)
            queryset = queryset.filter(users_accepted=accepted_by)
        return queryset

class PlaylistSavedByFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request: Request, queryset: QuerySet, view):
        _saved_by: str = request.query_params.get('saved_by')
        if _saved_by is not None:
            saved_by = int(_saved_by)
            queryset = queryset.filter(users_saved=saved_by)
        return queryset

class PlaylistSeenFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request: Request, queryset: QuerySet, view) -> QuerySet:
        seen = request.query_params.get('seen') == 'true'
        if seen:
            user: User = request.user
            queryset = queryset.filter(id__in=user.seen_playlists.all())
        return queryset
