from copy import copy
import json
import logging

from django.db.models import QuerySet
from django.conf import settings
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile
)
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.models import (
    Post,
    User,
    Activity,
)
from api.pagination import AppPageNumberPagination, get_page_size_from_request
from api.services.firebase import FirebaseService
from api.views.filters.post import PostCreatedByFilterBackend
from api.serializers.post import (
    PostValidationSerializer,
    PostDetailSerializer,
    PostViewSerializer
)
from api.utils.app_content import AppContentFileHandler
from api.views.filters.post import (
    PostCreatedByFilterBackend,
    PostSeenFilterBackend
)
from api.views.filters.user_block import UserBlockFilterBackend
from api.views.mixins.attachments import AttachmentsMixin
from api.views.mixins.comment import CommentMixin
from api.views.mixins.like import LikeMixin
from api.enums import ActivityType

class PostViewSet(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    LikeMixin,
    CommentMixin,
    AttachmentsMixin):

    queryset = Post.objects.all()
    filterset_fields = ()
    filter_backends = (
        PostCreatedByFilterBackend,
        PostSeenFilterBackend,
        DjangoFilterBackend,
        UserBlockFilterBackend,
    )

    # override
    def get_serializer_class(self):
        match self.action:
            case 'create':
                return PostDetailSerializer
            case 'update':
                return PostDetailSerializer
            case 'retrieve':
                if self.request.query_params.get('details', 'false').strip() == 'true':
                    return PostDetailSerializer
        return PostViewSerializer

    @transaction.atomic
    def create(self, request: Request) -> Response:
        try:
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
                json_data = json.loads(request.data.get('json', '{}'))
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

            if 'experience' in json_data and \
                json_data['experience'] is not None and \
                'playlist' in json_data and \
                json_data['playlist'] is not None:
                msg = 'Cannot make a post attached to both an post and a playlist'
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)

            validation_serializer = PostValidationSerializer(
                data=json_data,
                context=self.get_serializer_context())
            validation_serializer.is_valid(raise_exception=True)

            post: Post = validation_serializer.save(
                created_by=request.user)
            handler = AppContentFileHandler(
                app_content=post,
                video=uploaded_video,
                image=uploaded_image,
                thumb=uploaded_image_thumbnail)
            handler.validate_and_prep_simple_info()
            # TODO:
            # This will change to be a system where files are marked as
            # "needs compression" and do them on a compression server in a queue.
            handler.compress_or_save_where_needed()
            post.save()
            handler.dispose()

            activities: list[Activity] = []
            for mention in post.mentions.all():
                a = Activity(
                    type=ActivityType.MENTIONED_POST,
                    user=mention,
                    related_user=request.user,
                    post=post,
                    is_push=post.created_by.activity_push_pref \
                        and post.created_by.mention_push_pref)
                activities.append(a)
            Activity.objects.bulk_create(activities)
            try:
                fb_service = FirebaseService()
                for a in activities:
                    if not a.is_push:
                        continue
                    fb_service.push_activity_to_user(a)
            except:
                logger = logging.getLogger('app')
                logger.info('Error sending post mention notification')
            serializer = self.get_serializer(post)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            transaction.set_rollback(rollback=True)
            raise

    @transaction.atomic
    def update(self, request: Request, pk):
        try:
            # Don't use serializer.update as it deletes the mentions.
            request_user: User = request.user
            post: Post = self.get_object()
            if post.created_by != request_user:
                msg = 'You do not have permission to edit this post.'
                return Response(msg, status=status.HTTP_401_UNAUTHORIZED)
            old_mentions = list(post.mentions.all())

            data = request.data
            json_data: dict

            #! BACK COMPAT
            if 'json' in data:
                json_data = json.loads(data.get('json', '{}'))
                replace_highlight_image = json_data.get('replace_highlight_image')
                replace_highlight_image_thumbnail = json_data.get('replace_highlight_image_thumbnail')
                replace_video = json_data.get('replace_video')
            else:
                data = copy(request.data)
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

            json_data['id'] = pk
            validation_serializer = PostValidationSerializer(
                data=json_data,
                context=self.get_serializer_context())
            validation_serializer.is_valid(raise_exception=True)
            validated_data = validation_serializer.validated_data
            if 'experience' in json_data and \
                json_data['experience'] is not None and \
                'playlist' in json_data and \
                json_data['playlist'] is not None:
                msg = "Post's cannot have both a post and a playlist attached"
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)

            for key, value in validated_data.items():
                setattr(post, key, value)

            uploaded_video: InMemoryUploadedFile | TemporaryUploadedFile = None
            uploaded_image: InMemoryUploadedFile | TemporaryUploadedFile = None
            uploaded_image_thumbnail: InMemoryUploadedFile | TemporaryUploadedFile = None
            if replace_highlight_image:
                uploaded_image = None
                if 'highlight_image' in data:
                    uploaded_image = data['highlight_image']
                if uploaded_image is None:
                    post.highlight_image = None
                    post.highlight_image_thumbnail = None
            if replace_highlight_image_thumbnail:
                uploaded_image_thumbnail = None
                if 'highlight_image_thumbnail' in data:
                    uploaded_image_thumbnail = data['highlight_image_thumbnail']
                if uploaded_image_thumbnail is None:
                    post.highlight_image_thumbnail = None
            if replace_video:
                uploaded_video = None
                if 'video' in data:
                    uploaded_video = data['video']
                if uploaded_video is None:
                    post.video = None

            post.save()
            handler = AppContentFileHandler(
                app_content=post,
                video=uploaded_video,
                image=uploaded_image,
                thumb=uploaded_image_thumbnail)
            handler.validate_and_prep_simple_info()
            # TODO:
            # This will change to be a system where files are marked as
            # "needs compression" and do them on a compression server in a queue.
            handler.compress_or_save_where_needed()
            post.save()
            handler.dispose()

            new_mentions = list(post.mentions.all())
            to_notify = [ m for m in new_mentions if m not in old_mentions]
            activities: list[Activity] = []
            for mention in to_notify:
                a = Activity(
                    type=ActivityType.MENTIONED_POST,
                    user=mention,
                    related_user=request.user,
                    post=post,
                    is_push=post.created_by.activity_push_pref \
                        and post.created_by.mention_push_pref)
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
                logger.info('Error sending post mention notification')
            serializer = self.get_serializer(post)
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        except:
            transaction.set_rollback(rollback=True)
            raise

    def list(self, request: Request) -> Response:
        posts: QuerySet[Post] = self.get_queryset().order_by('-created_at')
        for filter_class in self.filter_backends:
            filter = filter_class()
            posts = filter.filter_queryset(request, posts, view=None)
        page_size = get_page_size_from_request(request, 10)
        paginator = AppPageNumberPagination(page_size=page_size)
        page = paginator.paginate_queryset(posts, request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_seen(self, request: Request, pk) -> Response:
        if not settings.SKIP_MARK_FOLLOW_FEED_SEEN:
            post: Post = self.get_object()
            user: User = request.user
            user.seen_posts.add(post)
        return Response()

    def destroy(self, request: Request, pk) -> Response:
        request_user: User = request.user
        post: Post = self.get_object()
        if post.created_by != request_user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
