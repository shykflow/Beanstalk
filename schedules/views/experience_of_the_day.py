from django.utils import timezone
from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from api.pagination import (
    AppPageNumberPagination,
    get_page_size_from_request,
)

from schedules.models import (
    ExperienceOfTheDaySchedule,
)
from schedules.serializers.experience_of_the_day import (
    ExperienceOfTheDayScheduleSerializer,
)

class ExperienceOfTheDayScheduleViewSet(viewsets.GenericViewSet):

    def get_queryset(
        self) -> QuerySet[ExperienceOfTheDaySchedule]:
        return ExperienceOfTheDaySchedule.objects \
            .filter(experience__is_deleted=False) \
            .prefetch_related('experience') \
            .order_by('-publish_at', '?')

    def _compute_now_local_time(
        self,
        query_params: dict) -> timezone.datetime:
        minutes_offset = int(query_params.get('minutes_offset', '0'))
        # Temporary fix for the phone app not sending the offset,
        # default to Utah's offset
        minutes_offset = int(query_params.get('minutes_offset', '-360'))
        now = timezone.datetime.now(tz=timezone.utc)
        local_offset = timezone.timedelta(minutes=minutes_offset)
        return now + local_offset


    def list(self, request: Request, *args, **kwargs) -> Response:
        query_params: dict = request.query_params
        now_local = self._compute_now_local_time(query_params)
        qs = self.get_queryset() \
            .filter(publish_at__lte=now_local)
        page_size = get_page_size_from_request(request, 10)
        paginator = AppPageNumberPagination(page_size=page_size)
        page = paginator.paginate_queryset(qs, request)
        serializer = ExperienceOfTheDayScheduleSerializer(
            page,
            many=True,
            context={'request': request})
        return paginator.get_paginated_response(serializer.data)


    @action(detail=False, methods=["get"])
    def current(self, request: Request) -> Response:
        query_params: dict = request.query_params
        now_local = self._compute_now_local_time(query_params)
        qs = self.get_queryset() \
            .filter(publish_at__lte=now_local)
        schedule = qs.first()
        if schedule is None:
            return Response(None)
        diff_from_now = now_local - schedule.publish_at
        diff_in_hours = diff_from_now.total_seconds() / 3600
        if diff_in_hours >= 24:
            # The most recent schedule is 1 or more days old
            return Response(None)
        serializer = ExperienceOfTheDayScheduleSerializer(
            schedule,
            context={'request': request})
        return Response(serializer.data)
