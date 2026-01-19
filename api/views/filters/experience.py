from django.db.models import QuerySet
from django.db.models.query import Q
from rest_framework import filters
from rest_framework.request import Request

from api.enums import Publicity
from api.models import User


class ExperienceCreatedByFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request: Request, queryset: QuerySet, view) -> QuerySet:
        created_by = request.query_params.get('created_by')
        if created_by is not None:
            queryset = queryset.filter(created_by_id=created_by)
            if created_by != request.user.id:
                filter_public = Q(visibility=Publicity.PUBLIC)
                filter_shared_with = Q(visibility=Publicity.INVITE, shared_with=request.user.id)
                queryset = queryset.filter(filter_public | filter_shared_with)
        return queryset

class ExperienceSeenFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request: Request, queryset: QuerySet, view) -> QuerySet:
        seen = request.query_params.get('seen') == 'true'
        if seen:
            user: User = request.user
            queryset = queryset.filter(id__in=user.seen_experiences.all())
        return queryset


class ExperienceCreatedByOrAcceptedByUserFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request: Request, queryset: QuerySet, view) -> QuerySet:
        created_or_accepted = request.query_params.get('created_or_accepted') == 'true'
        if created_or_accepted:
            user: User = request.user
            filter_created_by = Q(created_by_id=user)
            filter_accepted_by = Q(experienceaccept__user=user)
            queryset = queryset \
                .filter(filter_created_by | filter_accepted_by) \
                .distinct()
        return queryset
