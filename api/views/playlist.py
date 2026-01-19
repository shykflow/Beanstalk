import json
import logging

from django.conf import settings
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile
)
from django.db import transaction
from django.db.models import QuerySet, Count, Q
from django.db.utils import IntegrityError
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.enums import ActivityType
from api.models import (
    Activity,
    ExperienceAccept,
    Playlist,
    PlaylistCompletion,
    PlaylistPin,
    Post,
    User,
)
from api.pagination import AppPageNumberPagination, get_page_size_from_request
from api.serializers.playlist import (
    PlaylistValidationSerializer,
    PlaylistViewSerializer,
    PlaylistDetailSerializer,
)
from api.serializers.experience import ExperienceViewSerializer
from api.serializers.completion import CompletionSerializer
from api.services.firebase import FirebaseService
from api.serializers.post import PostViewSerializer
from api.utils import validate_start_and_end_dts
from api.utils.app_content import AppContentFileHandler
from api.views.filters.playlist import (
    PlaylistCreatedByFilterBackend,
    PlaylistAcceptedByFilterBackend,
    PlaylistNotPinnedByFilterBackend,
    PlaylistNotCreatedByFilterBackend,
    PlaylistSavedByFilterBackend,
    PlaylistSeenFilterBackend,
)
from api.views.filters.experience import ExperienceCreatedByFilterBackend
from api.views.filters.user_block import UserBlockFilterBackend
from api.views.mixins.accepted_users import AcceptedUsersMixin
from api.views.mixins.attachments import AttachmentsMixin
from api.views.mixins.comment import CommentMixin
from api.views.mixins.completed_users import CompletedUsersMixin
from api.views.mixins.like import LikeMixin
from api.views.mixins.cost_rating import CostRatingMixin
from api.views.mixins.post import PostMixin
from api.views.mixins.star_rating import StarRatingMixin


class PlaylistViewSet(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    CommentMixin,
    LikeMixin,
    CostRatingMixin,
    StarRatingMixin,
    AttachmentsMixin,
    AcceptedUsersMixin,
    CompletedUsersMixin,
    PostMixin):

    queryset = Playlist.objects.all().prefetch_related('experiences')
    filterset_fields = ()
    filter_backends = (
        PlaylistCreatedByFilterBackend,
        PlaylistAcceptedByFilterBackend,
        PlaylistSavedByFilterBackend,
        PlaylistSeenFilterBackend,
        DjangoFilterBackend,
        UserBlockFilterBackend,
        PlaylistNotPinnedByFilterBackend,
        PlaylistNotCreatedByFilterBackend,
    )

    # override
    def get_serializer_class(self):
        match self.action:
            case 'create' | 'update':
                return PlaylistDetailSerializer
            case 'retrieve':
                if self.request.query_params.get('details', 'false').strip() == 'true':
                    return PlaylistDetailSerializer
            case 'list':
                if self.request.query_params.get('details', 'false').strip() == 'true':
                    return PlaylistDetailSerializer
            # Used in the UserViewSet
            case 'pinned_playlists' | 'accepted_playlists' | 'saved_playlists':
                if self.request.query_params.get('details', 'false').strip() == 'true':
                    return PlaylistDetailSerializer
            case 'complete':
                return PostViewSerializer
        return PlaylistViewSerializer

    # override
    def get_serializer(self, *args, **kwargs):
        if self.action == 'retrieve' or self.action == 'list':
            kwargs['include_experience_ids'] =\
                self.request.query_params.get('include_experience_ids', 'true').strip() == 'true'
        return super().get_serializer(*args, **kwargs)

    def list(self, request: Request) -> Response:
        created_by = request.query_params.get('created_by')
        playlist_qs: QuerySet[Playlist] = self.get_queryset().order_by('-created_at')

        # TODO may need to filter experiences by visibility
        for filter_class in PlaylistViewSet.filter_backends:
            filter = filter_class()
            playlist_qs = filter.filter_queryset(request, playlist_qs, view=None)

        # Only annotate if the queryset is limited
        if created_by:
            playlist_qs = playlist_qs.annotate(
                num_completed_experiences=Count('experiences',
                Q(experiences__users_completed=request.user),
                distinct=True),
                num_experiences=Count('experiences',
                    distinct=True))

        page_size = get_page_size_from_request(request, 20)
        paginator = AppPageNumberPagination(page_size=page_size)
        page = paginator.paginate_queryset(playlist_qs, request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


    @transaction.atomic
    def create(self, request: Request, *args, **kwargs) -> Response:
        try:
            request_user: User = request.user
            data: dict[str, any] = request.data

            uploaded_video: InMemoryUploadedFile | TemporaryUploadedFile
            uploaded_image: InMemoryUploadedFile | TemporaryUploadedFile
            uploaded_image_thumbnail: InMemoryUploadedFile | TemporaryUploadedFile
            uploaded_video = data.get('video')
            uploaded_image = data.get('highlight_image')
            uploaded_image_thumbnail = data.get('highlight_image_thumbnail')

            json_data: dict
            #! BACK COMPAT
            if 'json' in data:
                json_data = json.loads(data.get('json', '{}'))
            else:
                if 'video' in data:
                    data.pop('video', None)
                if 'highlight_image' in data:
                    data.pop('highlight_image', None)
                if 'highlight_image_thumbnail' in data:
                    data.pop('highlight_image_thumbnail', None)
                json_data = data
            #! END BACK COMPAT
            #! BACK COMPATE REPLACEMENT
            # json_data = json.loads(data.get('json', '{}'))
            #! END BACK COMPAT REPLACEMENT


            validation_serializer = PlaylistValidationSerializer(
                data=json_data,
                context=self.get_serializer_context())
            validation_serializer.is_valid(raise_exception=True)
            validated_data = validation_serializer.validated_data
            validated_data['created_by'] = request_user

            try:
                validate_start_and_end_dts(
                    start=validated_data.get('start_time'),
                    end=validated_data.get('end_time'))
            except Exception as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

            playlist: Playlist = Playlist.objects.create(**validated_data)
            handler = AppContentFileHandler(
                app_content=playlist,
                video=uploaded_video,
                image=uploaded_image,
                thumb=uploaded_image_thumbnail)
            handler.validate_and_prep_simple_info()
            # TODO:
            # This will change to be a system where files are marked as
            # "needs compression" and do them on a compression server in a queue.
            handler.compress_or_save_where_needed()
            playlist.save()
            handler.dispose()

            activities: list[Activity] = []
            for mention in playlist.mentions.all():
                a = Activity(
                    type=ActivityType.MENTIONED_PLAYLIST,
                    user=mention,
                    related_user=request.user,
                    playlist=playlist,
                    is_push=request_user.activity_push_pref \
                        and request_user.mention_push_pref)
                a.save()
                activities.append(a)
            try:
                fb_service = FirebaseService()
                for a in activities:
                    if not a.is_push:
                        continue
                    fb_service.push_activity_to_user(a)
            except:
                logger = logging.getLogger('app')
                logger.info('Error sending experience mention notification')

            playlist.update_aggregated_categories()
            request_user.accepted_playlists.add(playlist)
            serializer = self.get_serializer(playlist)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except:
            transaction.set_rollback(rollback=True)
            raise


    @transaction.atomic
    def update(self, request: Request, pk):
        try:
            user: User = request.user
            playlist: Playlist = self.get_object()
            if playlist.created_by != user:
                msg = 'You do not have permission to edit this playlist'
                return Response(msg, status=status.HTTP_401_UNAUTHORIZED)
            data = request.data

            #! BACK COMPAT
            if 'json' in data:
                json_data = json.loads(data.get('json', '{}'))
                replace_highlight_image = json_data.get('replace_highlight_image')
                replace_highlight_image_thumbnail = json_data.get('replace_highlight_image_thumbnail')
                replace_video = json_data.get('replace_video')
            else:
                json_data = data
                replace_highlight_image = json_data.get('replace_highlight_image') == 'true'
                replace_highlight_image_thumbnail = json_data.get('replace_highlight_image_thumbnail') == 'true'
                replace_video = json_data.get('replace_video') == 'true'
            #! END BACK COMPAT
            #! BACK COMPATE REPLACEMENT
            # json_data = json.loads(data.get('json', '{}'))
            # replace_highlight_image = json_data.get('replace_highlight_image')
            # replace_highlight_image_thumbnail = json_data.get('replace_highlight_image_thumbnail')
            # replace_video = json_data.get('replace_video')
            #! END BACK COMPAT REPLACEMENT

            old_mentions = playlist.mentions.all()
            validation_serializer = PlaylistValidationSerializer(
                data=json_data,
                context=self.get_serializer_context())
            validation_serializer.is_valid(raise_exception=True)
            validated_data = validation_serializer.validated_data

            submitted_start_time = validated_data.get('start_time')
            submitted_end_time = validated_data.get('end_time')
            if (playlist.start_time != submitted_start_time or
                playlist.end_time != submitted_end_time):
                try:
                    validate_start_and_end_dts(
                        start=submitted_start_time,
                        end=submitted_end_time)
                except Exception as e:
                    return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

            for key, value in validated_data.items():
                setattr(playlist, key, value)

            uploaded_video: InMemoryUploadedFile | TemporaryUploadedFile = None
            uploaded_image: InMemoryUploadedFile | TemporaryUploadedFile = None
            uploaded_image_thumbnail: InMemoryUploadedFile | TemporaryUploadedFile = None
            if replace_highlight_image:
                uploaded_image = None
                if 'highlight_image' in data:
                    uploaded_image = data['highlight_image']
                if uploaded_image is None:
                    playlist.highlight_image = None
                    playlist.highlight_image_thumbnail = None
            if replace_highlight_image_thumbnail:
                uploaded_image_thumbnail = None
                if 'highlight_image_thumbnail' in data:
                    uploaded_image_thumbnail = data['highlight_image_thumbnail']
                if uploaded_image_thumbnail is None:
                    playlist.highlight_image_thumbnail = None
            if replace_video:
                uploaded_video = None
                if 'video' in data:
                    uploaded_video = data['video']
                if uploaded_video is None:
                    playlist.video = None

            playlist.save()
            handler = AppContentFileHandler(
                app_content=playlist,
                video=uploaded_video,
                image=uploaded_image,
                thumb=uploaded_image_thumbnail)
            handler.validate_and_prep_simple_info()
            # TODO:
            # This will change to be a system where files are marked as
            # "needs compression" and do them on a compression server in a queue.
            handler.compress_or_save_where_needed()
            playlist.save()
            handler.dispose()

            to_notify = playlist.mentions.all().difference(old_mentions)
            activities: list[Activity] = []
            for mention in to_notify:
                a = Activity(
                    type=ActivityType.MENTIONED_PLAYLIST,
                    user=mention,
                    related_user=request.user,
                    playlist=playlist,
                    is_push=playlist.created_by.activity_push_pref \
                        and playlist.created_by.mention_push_pref)
                a.save()
                activities.append(a)

            try:
                fb_service = FirebaseService()
                for a in activities:
                    if not a.is_push:
                        continue
                    fb_service.push_activity_to_user(a)
            except:
                logger = logging.getLogger('app')
                logger.info('Error sending experience mention notification')

            playlist.update_aggregated_categories()
            serializer = self.get_serializer(playlist)
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        except:
            transaction.set_rollback(rollback=True)
            raise

    def destroy(self, request: Request, pk, *args, **kwargs) -> Response:
        playlist: Playlist = self.get_object()
        if playlist.created_by != request.user:
            msg = 'You do not have permission to delete this playlist'
            return Response(msg, status=status.HTTP_401_UNAUTHORIZED)
        playlist.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def mark_seen(self, request: Request, pk) -> Response:
        if not settings.SKIP_MARK_FOLLOW_FEED_SEEN:
            playlist: Playlist = self.get_object()
            user: User = request.user
            user.seen_playlists.add(playlist)
        return Response()

    @action(detail=True, methods=['post', 'get', 'delete'])
    def experiences(self, request: Request, pk) -> Response:
        playlist: Playlist = self.get_object()
        if request.method == 'GET':
            qs = playlist.experiences \
                .order_by('-created_at')
            page_size = get_page_size_from_request(request, 10)
            paginator = AppPageNumberPagination(page_size=page_size)
            page = paginator.paginate_queryset(qs, request)
            context = {'request': request,}
            serializer = ExperienceViewSerializer(page, many=True, context=context)
            return paginator.get_paginated_response(serializer.data)
        if playlist.created_by != request.user:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        experience_ids = request.data.get('experiences')
        if not experience_ids or type(experience_ids) is not list:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            if request.method == 'POST':
                playlist.experiences.add(*experience_ids)
            else:
                playlist.experiences.remove(*experience_ids)
            playlist.update_aggregated_categories()
            return Response()
        except IntegrityError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    @action(detail=True, methods=['post', 'delete'])
    def accept(self, request: Request, pk) -> Response:
        playlist: Playlist = self.get_object()
        user: User = request.user
        if request.method == 'POST':
            accept_experiences = request.query_params.get('accept_experiences') == 'true'
            user.accepted_playlists.add(pk)
            activity: Activity
            try:
                # create playlist activity
                if playlist.created_by is not None and playlist.created_by != user:
                    activity = Activity(
                        type=ActivityType.ACCEPTED_PLAYLIST,
                        user=playlist.created_by,
                        related_user=user,
                        playlist=playlist,
                        is_push=playlist.created_by.activity_push_pref and playlist.created_by.accept_complete_push_pref)
                    activity.save()
                    # Client wants to hide that accepting exists for now
                    # try:
                    #     if activity.is_push:
                    #         fb_service = FirebaseService()
                    #         fb_service.push_activity_to_user(activity)
                    # except Exception as e:
                    #     logger = logging.getLogger('app')
                    #     logger.info('Error sending comment notification')
                if accept_experiences:
                    experiences_to_accept = playlist.experiences \
                        .exclude(pk__in=user.accepted_experiences.all())
                    accepts = [
                        ExperienceAccept(experience=exp, user=user)
                        for exp in experiences_to_accept
                    ]
                    ExperienceAccept.objects.bulk_create(accepts)
                    experience_accept_activities: list[Activity] = []
                    for accept in accepts:
                        if accept.experience.created_by is None or accept.experience.created_by != user:
                            continue
                        is_push = accept.experience.created_by != playlist.created_by \
                            and accept.experience.created_by.activity_push_pref \
                            and accept.experience.created_by.mention_push_pref
                        activity = Activity(
                            type=ActivityType.ACCEPTED_EXPERIENCE,
                            user=playlist.created_by,
                            related_user=user,
                            experience=accept.experience,
                            is_push=is_push)
                        experience_accept_activities.append(activity)
                    Activity.objects.bulk_create(experience_accept_activities)
                    data = {'num_accepted_experiences': len(accepts)}
                    return Response(data)
            except Exception as e:
                transaction.set_rollback(rollback=True)
                raise e
            # Send notification to playlist creator
            return Response()
        else:
            user.accepted_playlists.remove(pk)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'])
    def save(self, request: Request, pk) -> Response:
        if request.method == 'POST':
            request.user.saved_playlists.add(pk)
            return Response()
        else:
            request.user.saved_playlists.remove(pk)
            return Response(status=status.HTTP_204_NO_CONTENT)


    @action(detail=True, methods=['post', 'delete'])
    def pin(self, request: Request, pk) -> Response:
        if request.method == 'POST':
            # always pin to end
            user :User = request.user
            position: int
            last_pin = PlaylistPin.objects.filter(user=user).order_by('position').last()
            if last_pin is None:
                position = 0
            else:
                position = last_pin.position + 1
            user.pinned_playlists.add(pk, through_defaults={'position':position})
            return Response()
        else:
            request.user.pinned_playlists.remove(pk)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def complete(self, request: Request, pk) -> Response:
        user: User = request.user
        validation_serializer = CompletionSerializer(data=request.data,
            context=self.get_serializer_context())
        validation_serializer.is_valid(raise_exception=True)
        validated_data = validation_serializer.validated_data

        playlist: Playlist = self.get_object()
        if user.completed_playlists.filter(id=pk).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Auto add the experience to the user added for now
        user.accepted_playlists.add(playlist)

        experience_qs = playlist.experiences.all()
        experience_filters = (
            ExperienceCreatedByFilterBackend,
            DjangoFilterBackend,
            UserBlockFilterBackend,
        )
        for filter_class in experience_filters:
            filter = filter_class()
            experience_qs = filter.filter_queryset(request, experience_qs, view=None)
        if not experience_qs.exists() or experience_qs.exclude(users_completed=user).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        offset = validated_data['minutes_offset']
        if not playlist.valid_completion_time(offset):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        completion = PlaylistCompletion(user=user, playlist_id=pk)
        completion.save()
        try:
            if playlist.created_by is not None and playlist.created_by != user:
                activity = Activity(
                    type=ActivityType.COMPLETED_PLAYLIST,
                    user=playlist.created_by,
                    related_user=request.user,
                    playlist=playlist,
                    is_push=playlist.created_by.activity_push_pref and playlist.created_by.accept_complete_push_pref)
                activity.save()
                # Playlist completions are sent immediately,
                #   while experience completions are sent on the cron.
                # Do not send experience completion notifications to users who
                #   already received the playlist completion notifications.
                Activity.objects.filter(
                    user=playlist.created_by,
                    related_user=request.user,
                    experience__in=playlist.experiences.all(),
                    is_push=True) \
                        .update(is_push=False)
                # Send notification to playlist creator
                try:
                    if activity.is_push:
                        fb_service = FirebaseService()
                        fb_service.push_activity_to_user(activity)
                except Exception as e:
                    logger = logging.getLogger('app')
                    logger.info('Error sending comment notification')
        except Exception as e:
            transaction.set_rollback(rollback=True)
            raise e

        # Create post
        try:
            post_data = validated_data['post']
        except KeyError:
            return Response()
        try:
            post = Post(
                created_by=user,
                text=post_data['text'] if 'text' in post_data else None,
                playlist_completion=completion,
                playlist_id=pk,)
            post.save()
            activities = []
            for mention in post.mentions.all():
                activity = Activity(
                    type=ActivityType.MENTIONED_POST,
                    user=mention,
                    related_user=request.user,
                    post=post,
                    is_push=post.created_by.activity_push_pref and post.created_by.mention_push_pref)
                activities.append(activity)
            Activity.objects.bulk_create(activities)
            try:
                fb_service = FirebaseService()
                for a in activities:
                    if not a.is_push:
                        continue
                    fb_service.push_activity_to_user(a)
            except Exception as e:
                logger = logging.getLogger('app')
                msg = 'Error sending experience completion post mention notification'
                logger.info(msg)
        except:
            transaction.set_rollback(rollback=True)
            raise
        return_serializer = self.get_serializer(post)
        return Response(return_serializer.data, status=status.HTTP_201_CREATED)
