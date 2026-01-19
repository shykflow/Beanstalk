from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import BooleanField, Case, Count, Value, When

from api.models import Activity, AggregateActivity
from api.serializers.activity import ActivityFCMDataSerializer, AggregateActivitySerializer

class ActivityViewSet(viewsets.GenericViewSet,):

    @action(detail=False, methods=["get"],)
    def list_aggregated(self, request: Request, *args, **kwargs) -> Response:
        aggregate_activities_qs = AggregateActivity.objects \
            .filter(user=request.user) \
            .order_by('-related_time','-created_at')[0:30] \
            .annotate(
                following_related_user = Case(
                    When(
                        related_user__in=request.user.follows.all(),
                        then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField())) \
            .prefetch_related(
                'user',
                'related_user',
                'post',
                'experience',
                'playlist',
            )
        serializer = AggregateActivitySerializer(aggregate_activities_qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"],)
    def list_unaggregated(self, request: Request, *args, **kwargs) -> Response:
        activities_qs = Activity.objects \
            .filter(user=request.user, aggregated=False) \
            .order_by('-related_time','-created_at')[0:30] \
            .annotate(
                following_related_user = Case(
                    When(
                        related_user__in=request.user.follows.all(),
                        then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField())) \
            .prefetch_related(
                'related_user',
                'post',
                'experience',
                'playlist',
                # 'experience_stack,
            )
        serializer = ActivityFCMDataSerializer(activities_qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"],)
    def unseen_activity_counts(self, request: Request, *args, **kwargs) -> Response:
        '''Get number of unseen activities grouped by type'''
        activities = Activity.objects \
            .filter(user=request.user, seen=False) \
            .values('type') \
            .annotate(total=Count('type'))
        return Response(activities)

    @action(detail=False, methods=["get"],)
    def unseen_count(self, request: Request, *args, **kwargs) -> Response:
        count = Activity.objects \
            .filter(user=request.user, seen=False) \
            .count()
        return Response(count)

    @action(detail=False, methods=["post"],)
    def mark_all_seen(self, request: Request, *args, **kwargs) -> Response:
        Activity.objects \
            .filter(user=request.user, seen=False) \
            .update(seen=True)
        return Response()
