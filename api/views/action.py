import pytz
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Count, Q, F
from itertools import chain
from django_filters.rest_framework import DjangoFilterBackend
from api.models import User, Experience, Playlist, Post
from api.serializers.experience import ExperienceViewSerializer
from api.serializers.playlist import PlaylistViewSerializer
from api.serializers.combined_content_serializer import CombinedContentSerializer
from api.utils.measure_time_diff import MeasureTimeDiff
from api.views.filters.experience import ExperienceCreatedByFilterBackend
from api.views.filters.user_block import UserBlockFilterBackend
from api.pagination import AppPageNumberPagination, get_page_size_from_request


class ActionViewSet(viewsets.GenericViewSet,):
    filter_backends = (
        ExperienceCreatedByFilterBackend,
        DjangoFilterBackend,
        UserBlockFilterBackend,
    )

    @action(detail=False, methods=["get"])
    def content_counts(self, request: Request) -> Response:
        user: User = request.user
        experience_qs = Experience.objects.all()
        playlist_qs = Playlist.objects.all()
        post_qs = Post.objects.all()
        now = timezone.now()
        month_from_now = timezone.now() + timezone.timedelta(days=30)
        for filter_class in self.filter_backends:
            filter = filter_class()
            experience_qs = filter.filter_queryset(request, experience_qs, view=None)
            playlist_qs = filter.filter_queryset(request, playlist_qs, view=None)
            post_qs = filter.filter_queryset(request, post_qs, view=None)

        experience_counts = experience_qs.aggregate(
            experience_count=Count(
                'id',
                filter=Q(users_accepted=user),
                distinct=True),
            # Don't rely on the fact that completed experiences should also be accepted
            accepted_completed_experience_count=Count(
                'id',
                filter=Q(users_accepted=user) & Q(users_completed=user),
                distinct=True),
            completed_experience_count=Count(
                'id',
                filter=Q(users_completed=user),
                distinct=True),
            created_experience_count=Count(
                'id',
                filter=Q(created_by=user),
                distinct=True),
            saved_experience_count=Count(
                'id',
                filter=Q(users_saved=user),
                distinct=True),
            personal_bucket_list_count=Count(
                'id',
                filter=Q(users_bucket_list=user),
                distinct=True),
            upcoming_experience_count=Count(
                'id',
                filter=Q(users_accepted=user) & \
                    Q(end_time__lt=month_from_now) & \
                    Q(end_time__gt=now),
                distinct=True),
            upcoming_accepted_completed_experience_count=Count(
                'id',
                filter=Q(users_accepted=user) & \
                    Q(end_time__lt=month_from_now) & \
                    Q(end_time__gt=now) & \
                    Q(users_completed=user),
                distinct=True))

        playlist_counts = playlist_qs.aggregate(
            completed_playlist_count=Count(
                'id',
                filter=Q(users_accepted=user) & Q(users_completed=user),
                distinct=True),
            upcoming_playlist_count=Count(
                'id',
                filter=Q(users_accepted=user) & \
                    Q(end_time__lt=month_from_now) & \
                    Q(end_time__gt=now),
                distinct=True),
            saved_playlist_count=Count(
                'id',
                filter=Q(users_saved=user),
                distinct=True),
            upcoming_accepted_completed_playlist_count=Count(
                'id',
                filter=Q(users_accepted=user) & \
                    Q(end_time__lt=month_from_now) & \
                    Q(end_time__gt=now) & \
                    Q(users_completed=user),
                distinct=True))

        post_count = post_qs.filter(created_by=user).count()

        data = {
            **experience_counts,
            **playlist_counts,
            'post_count': post_count,
            }
        data['active_experience_count'] = data['experience_count'] - data.pop('accepted_completed_experience_count')
        data['upcoming_experience_count'] = data['upcoming_experience_count'] - data.pop('upcoming_accepted_completed_experience_count')
        data['upcoming_playlist_count'] = data['upcoming_playlist_count'] - data.pop('upcoming_accepted_completed_playlist_count')
        data['saved_for_later_count'] = data['saved_experience_count'] + data['saved_playlist_count']

        return Response(data)

    @action(detail=False, methods=["get"])
    def time_restricted_content(self, request: Request) -> Response:
        version = request.query_params.get('version', '1').strip()

        #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=19)
        if version == '1':
            return self._time_restricted_content_v1(request)
        elif version == '2':
            with MeasureTimeDiff(label='content_from_category_id'):
                return self._time_restricted_content_v2(request)
        #! END BACK COMPAT (don't need v1 after everyone updates app to version 19)

        msg = 'Only `version` 1 or 2 are acceptable'
        return Response(msg, status=status.HTTP_400_BAD_REQUEST)

    def _time_restricted_content_v1(self, request: Request) -> Response:
        start_str = request.query_params.get('start')
        end_str = request.query_params.get('end')
        minutes_offset_str = request.query_params.get('minutes_offset')
        if start_str is None or end_str is None or minutes_offset_str is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        minutes_offset = float(minutes_offset_str)
        if minutes_offset > 1400 or minutes_offset < -1440:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        start: timezone.datetime = timezone.datetime.strptime(start_str, format('%Y-%m-%d'))\
            .replace(tzinfo=timezone.utc)
        end: timezone.datetime = timezone.datetime.strptime(end_str, format('%Y-%m-%d'))\
            .replace(tzinfo=timezone.utc)
        now = timezone.datetime.now(tz=timezone.utc)
        if start > end or (end - start).days > 31:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        experience_qs = Experience.objects \
            .all()
        playlist_qs = Playlist.objects \
            .all()
        for filter_class in self.filter_backends:
            filter = filter_class()
            experience_qs = filter.filter_queryset(request, experience_qs, view=None)
            playlist_qs = filter.filter_queryset(request, playlist_qs, view=None)
        timedelta = timezone.timedelta(minutes=minutes_offset)

        experiences = experience_qs.filter(
            (Q(use_local_time=True)
                & Q(end_time__gte=start + timedelta, end_time__lte=end + timedelta)
                & Q(end_time__gt=now + timedelta))
            | (Q(use_local_time=False)
                & Q(end_time__gte=start, end_time__lte=end)
                & Q(end_time__gt=now)))
        experiences_serializer = ExperienceViewSerializer(
            experiences,
            many=True,
            context={'request': request})

        playlists = playlist_qs.filter(
            (Q(use_local_time=True)
                & Q(end_time__gte=start + timedelta, end_time__lte=end + timedelta)
                & Q(end_time__gt=now + timedelta))
            | (Q(use_local_time=False)
                & Q(end_time__gte=start, end_time__lte=end)
                & Q(end_time__gt=now)))
        playlist_serializer = PlaylistViewSerializer(
            playlists,
            many=True,
            context={'request': request})

        data = experiences_serializer.data + playlist_serializer.data
        return Response(data)

    
    def _time_restricted_content_v2(self, request: Request) -> Response:
        start_str = request.query_params.get('start')
        end_str = request.query_params.get('end')
        minutes_offset_str = request.query_params.get('minutes_offset')
        if start_str is None or end_str is None or minutes_offset_str is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        minutes_offset_int = int(minutes_offset_str)
        if minutes_offset_int > 1400 or minutes_offset_int < -1440:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        start: timezone.datetime = timezone.datetime.fromisoformat(start_str)
        end: timezone.datetime = timezone.datetime.fromisoformat(end_str)
        if start > end or (end - start).days > 31:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        tz = pytz.timezone('UTC')
        start = tz.localize(start)
        end = tz.localize(end)
        minutes_offset = timezone.timedelta(minutes=minutes_offset_int)

        experience_qs = Experience.objects \
            .all()
        playlist_qs = Playlist.objects \
            .all()
        for filter_class in self.filter_backends:
            filter = filter_class()
            experience_qs = filter.filter_queryset(request, experience_qs, view=None)
            playlist_qs = filter.filter_queryset(request, playlist_qs, view=None)

        use_local_time_q = Q(use_local_time=True) \
              & Q(end_time__gte=start, end_time__lte=end)
        use_global_time_q = Q(use_local_time=False) \
                & Q(end_time__gte=start - minutes_offset, \
                    end_time__lte=end - minutes_offset)
        time_filter_q = use_local_time_q | use_global_time_q

        local_time_qs = experience_qs.filter(use_local_time_q)
        global_time_qs = experience_qs.filter(use_global_time_q)

        experience_qs = (local_time_qs | global_time_qs).distinct()

        experiences_serializer = ExperienceViewSerializer(
            experience_qs,
            many=True,
            context={'request': request})

        playlist_qs = playlist_qs.filter(time_filter_q)
        playlist_serializer = PlaylistViewSerializer(
            playlist_qs,
            many=True,
            context={'request': request})

        data = experiences_serializer.data + playlist_serializer.data
        return Response(data)

    @action(detail=False, methods=["get"])
    def saved_content(self, request: Request) -> Response:
        # TODO order by when items were saved
        playlist_qs = Playlist.objects.filter(users_saved=request.user)
        for filter_class in self.filter_backends:
            filter = filter_class()
            playlist_qs = filter.filter_queryset(request, playlist_qs, view=None)
        playlist_qs = playlist_qs.annotate(
            num_completed_experiences=Count(
                Q(experiences__users_completed=request.user),
                distinct=True),
            num_experiences=Count('id', distinct=True),
            saved_at=F('playlistsave__created_at'))
        experience_qs = Experience.objects.filter(users_saved=request.user)
        for filter_class in self.filter_backends:
            filter = filter_class()
            experience_qs = filter.filter_queryset(request, experience_qs, view=None)
        experience_qs = experience_qs.annotate(
            saved_at=F('experiencesave__created_at'))

        page_size = get_page_size_from_request(request, 10)
        paginator = AppPageNumberPagination(page_size=page_size)
        saves = sorted(
            chain(playlist_qs, experience_qs),
            key=lambda objects: objects.saved_at)

        page = paginator.paginate_queryset(saves, request)
        context = {'request': request,}
        serializer = CombinedContentSerializer(page, many=True, context=context)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"])
    def bucket_list_content(self, request: Request) -> Response:
        experience_qs = Experience.objects.filter(users_bucket_list=request.user)
        for filter_class in self.filter_backends:
            filter = filter_class()
            experience_qs = filter.filter_queryset(request, experience_qs, view=None)
        experience_qs = experience_qs.annotate(
            saved_at=F('savepersonalbucketlist__created_at'))

        page_size = get_page_size_from_request(request, 10)
        paginator = AppPageNumberPagination(page_size=page_size)
        saves = sorted(experience_qs,
            key=lambda objects: objects.saved_at)

        page = paginator.paginate_queryset(saves, request)
        context = {'request': request,}
        serializer = ExperienceViewSerializer(page, many=True, context=context)
        return paginator.get_paginated_response(serializer.data)
