import logging
import json
from copy import copy

from django.conf import settings
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile
)
from django.db import transaction
from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import mixins, status, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.enums import (
    ActivityType,
    UserType,
)
from api.models import (
    Activity,
    CustomCategory,
    Playlist,
    Experience,
    User,
)
from api.models.accept import ExperienceAccept
from api.models.activity import Activity
from api.models.experience_completion import ExperienceCompletion
from api.models.post import Post
from api.pagination import AppPageNumberPagination, get_page_size_from_request
from api.serializers.experience import (
    ExperienceValidationSerializer,
    ExperienceViewSerializer,
    ExperienceDetailSerializer
)
from api.serializers.completion import CompletionSerializer
from api.serializers.cost_rating import CostRatingSerializer
from api.serializers.post import PostViewSerializer
from api.utils import validate_start_and_end_dts
from api.utils.app_content import AppContentFileHandler
from api.views.filters.experience import (
    ExperienceCreatedByFilterBackend,
    ExperienceSeenFilterBackend,
    ExperienceCreatedByOrAcceptedByUserFilterBackend,
)
from api.views.filters.user_block import UserBlockFilterBackend
from api.views.mixins.accepted_users import AcceptedUsersMixin
from api.views.mixins.attachments import AttachmentsMixin
from api.views.mixins.comment import CommentMixin
from api.views.mixins.completed_users import CompletedUsersMixin
from api.views.mixins.like import LikeMixin
from api.views.mixins.cost_rating import CostRatingMixin
from api.views.mixins.star_rating import StarRatingMixin
from api.views.mixins.post import PostMixin
from api.services.firebase import FirebaseService
from lf_service.category import LifeFrameCategoryService

class ExperienceViewSet(
        viewsets.GenericViewSet,
        CommentMixin,
        LikeMixin,
        mixins.RetrieveModelMixin,
        CostRatingMixin,
        StarRatingMixin,
        AttachmentsMixin,
        AcceptedUsersMixin,
        CompletedUsersMixin,
        PostMixin):
    filterset_fields = ()
    filter_backends = (
        ExperienceCreatedByFilterBackend,
        ExperienceSeenFilterBackend,
        ExperienceCreatedByOrAcceptedByUserFilterBackend,
        DjangoFilterBackend,
        UserBlockFilterBackend,
    )

    def get_queryset(self):
        return Experience.objects \
            .all() \
            .prefetch_related('likes')

    # override
    def get_serializer_class(self):
        match self.action:
            case 'create':
                return ExperienceDetailSerializer
            case 'retrieve':
                if self.request.query_params.get('details', 'false').strip() == 'true':
                    return ExperienceDetailSerializer
            case 'list':
                if self.request.query_params.get('details', 'false').strip() == 'true':
                    return ExperienceDetailSerializer
            case 'complete':
                return PostViewSerializer
            case 'cost_rating':
                return CostRatingSerializer
        return ExperienceViewSerializer

    # override
    def get_serializer(self, *args, **kwargs) -> serializers.Serializer:
        return super().get_serializer(*args, **kwargs)

    def list(self, request: Request) -> Response:
        experiences: QuerySet[Experience] = self.get_queryset().order_by('-created_at')
        accepted_by = request.query_params.get('accepted_by')

        for filter_class in ExperienceViewSet.filter_backends:
            filter = filter_class()
            experiences = filter.filter_queryset(request, experiences, view=None)

        # Excludes Completed
        if accepted_by is not None:
            completed_experience_ids = ExperienceCompletion.objects \
                .filter(user=accepted_by) \
                .values_list('experience__id', flat=True)
            ordered_accepted_experience_ids = ExperienceAccept.objects \
                .filter(user=accepted_by) \
                .order_by('-created_at') \
                .values_list('experience__id', flat=True)
            experiences = experiences\
                .filter(id__in=ordered_accepted_experience_ids)\
                .exclude(id__in=completed_experience_ids)

            # If the decision is made to go back to not filtering out completed when asking for accepted use this:
            # # Accepted activities are ordered by if they are completed and, when they were accepted
            # experiences = experiences.filter(id__in=ordered_accepted_experience_ids) \
            #     .annotate(user_completed = Case(
            #         When(id__in=completed_experience_ids,
            #             then=Value(True)),
            #         default=Value(False),
            #         output_field=BooleanField()))

            experience_dict = dict([(obj.id, obj) for obj in experiences])
            # Sort based on when the accept was created
            experiences = [
                experience_dict.get(id)
                for id in ordered_accepted_experience_ids
                if id in experience_dict]
            # # Sort the items based on if they have been completed
            # experiences.sort(key=lambda x: x.user_completed)

        page_size = get_page_size_from_request(request, 10)
        paginator = AppPageNumberPagination(page_size=page_size)
        page = paginator.paginate_queryset(experiences, request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @transaction.atomic
    def create(self, request: Request, *args, **kwargs) -> Response:
        try:
            request_user : User = request.user
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

            validation_serializer = ExperienceValidationSerializer(
                data=json_data,
                context=self.get_serializer_context())
            validation_serializer.is_valid(raise_exception=True)
            validated_data = validation_serializer.validated_data

            try:
                validate_start_and_end_dts(
                    start=validated_data.get('start_time'),
                    end=validated_data.get('end_time'))
            except Exception as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

            if request_user.user_type != UserType.PARTNER:
                parner_only_fields = (
                    'reservation_link',
                    'menu_link',
                    'purchase_link',
                )
                for field in parner_only_fields:
                    value = validated_data.get(field)
                    if value is not None:
                        msg = f'{field} is only editable by parners'
                        return Response(msg, status=status.HTTP_401_UNAUTHORIZED)

            custom_category_names = validated_data.get('custom_categories')
            all_custom_categories = []
            if custom_category_names is not None:
                existing_categories = CustomCategory.objects.filter(name__in=custom_category_names).all()
                new_categories = []
                existing_names = [cat.name for cat in existing_categories]
                for name in custom_category_names:
                    if name not in existing_names:
                        new_categories.append(CustomCategory.objects.create(name=name))
                all_custom_categories = new_categories + [x for x in existing_categories]

            experience: Experience = validation_serializer.save(
                custom_categories=all_custom_categories,
                created_by=request.user)

            handler = AppContentFileHandler(
                app_content=experience,
                video=uploaded_video,
                image=uploaded_image,
                thumb=uploaded_image_thumbnail)
            handler.validate_and_prep_simple_info()
            # TODO:
            # This will change to be a system where files are marked as
            # "needs compression" and do them on a compression server in a queue.
            handler.compress_or_save_where_needed()
            experience.save()
            handler.dispose()

            activities: list[Activity] = []
            for mention in experience.mentions.all():
                a = Activity(
                    type=ActivityType.MENTIONED_EXPERIENCE,
                    user=mention,
                    related_user=request.user,
                    experience=experience,
                    is_push=experience.created_by.activity_push_pref \
                        and experience.created_by.mention_push_pref)
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

            request_user.accepted_experiences.add(experience)

            if ('add_to_playlists' in json_data):
                add_to_playlists: list[int] = json_data.getlist('add_to_playlists')
                for id in add_to_playlists:
                    playlist: Playlist =  Playlist.objects.get(id=id)
                    playlist.experiences.add(experience)

            serializer = self.get_serializer(experience)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except:
            transaction.set_rollback(rollback=True)
            raise

    @transaction.atomic
    def update(self, request: Request, pk):
        # Don't use serializer.update as it deletes the mentions.
        try:
            request_user: User = request.user
            experience: Experience = self.get_object()
            if experience.created_by != request_user:
                msg = 'You do not have permission to edit this experience.'
                return Response(msg, status=status.HTTP_401_UNAUTHORIZED)
            old_mentions = list(experience.mentions.all())

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
            # replace_video = json_data.get('replace_video')``
            #! END BACK COMPAT REPLACEMENT

            # If `id` is not set, the serializer update function will duplicate the experience.
            json_data['id'] = pk

            validation_serializer = ExperienceValidationSerializer(
                data=json_data,
                context=self.get_serializer_context())
            validation_serializer.is_valid(raise_exception=True)
            validated_data = validation_serializer.validated_data

            submitted_start_time = validated_data.get('start_time')
            submitted_end_time = validated_data.get('end_time')
            if (experience.start_time != submitted_start_time or
                experience.end_time != submitted_end_time):
                try:
                    validate_start_and_end_dts(
                        start=submitted_start_time,
                        end=submitted_end_time)
                except Exception as e:
                    return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

            if request_user.user_type != UserType.PARTNER:
                parner_only_fields = (
                    'reservation_link',
                    'menu_link',
                    'purchase_link',
                )
                for field in parner_only_fields:
                    value = validated_data.get(field)
                    if value != getattr(experience, field):
                        msg = f'{field} is only editable by parners'
                        return Response(msg, status=status.HTTP_401_UNAUTHORIZED)

            file_keys = (
                'video',
                'highlight_image',
                'highlight_image_thumbnail',
            )

            custom_category_names = []
            if 'custom_categories' in validated_data.keys():
                custom_category_names = validated_data.pop('custom_categories')

            for key, value in validated_data.items():
                if key in file_keys:
                    continue
                setattr(experience, key, value)

            uploaded_video: InMemoryUploadedFile | TemporaryUploadedFile = None
            uploaded_image: InMemoryUploadedFile | TemporaryUploadedFile = None
            uploaded_image_thumbnail: InMemoryUploadedFile | TemporaryUploadedFile = None
            if replace_highlight_image:
                uploaded_image = None
                if 'highlight_image' in data:
                    uploaded_image = data['highlight_image']
                if uploaded_image is None:
                    experience.highlight_image = None
                    experience.highlight_image_thumbnail = None
            if replace_highlight_image_thumbnail:
                uploaded_image_thumbnail = None
                if 'highlight_image_thumbnail' in data:
                    uploaded_image_thumbnail = data['highlight_image_thumbnail']
                if uploaded_image_thumbnail is None:
                    experience.highlight_image_thumbnail = None
            if replace_video:
                uploaded_video = None
                if 'video' in data:
                    uploaded_video = data['video']
                if uploaded_video is None:
                    experience.video = None

            existing_categories = CustomCategory.objects.filter(name__in=custom_category_names).all()
            new_categories = []
            existing_names = [cat.name for cat in existing_categories]
            for name in custom_category_names:
                if name not in existing_names:
                    new_categories.append(CustomCategory.objects.create(name=name))
            experience.custom_categories.set([x for x in existing_categories] + new_categories)

            experience.save()
            handler = AppContentFileHandler(
                app_content=experience,
                video=uploaded_video,
                image=uploaded_image,
                thumb=uploaded_image_thumbnail)
            handler.validate_and_prep_simple_info()
            # TODO:
            # This will change to be a system where files are marked as
            # "needs compression" and do them on a compression server in a queue.
            handler.compress_or_save_where_needed()
            experience.save()
            handler.dispose()

            new_mentions = list(experience.mentions.all())
            to_notify = [ m for m in new_mentions if m not in old_mentions]
            activities: list[Activity] = []
            for mention in to_notify:
                a = Activity(
                    type=ActivityType.MENTIONED_EXPERIENCE,
                    user=mention,
                    related_user=request.user,
                    experience=experience,
                    is_push=experience.created_by.activity_push_pref \
                        and experience.created_by.mention_push_pref)
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
            serializer = self.get_serializer(experience)
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        except:
            transaction.set_rollback(rollback=True)
            raise

    @action(detail=True, methods=['post'])
    def mark_seen(self, request: Request, pk) -> Response:
        if not settings.SKIP_MARK_FOLLOW_FEED_SEEN:
            experience: Experience = self.get_object()
            user: User = request.user
            user.seen_experiences.add(experience)
        return Response()

    @transaction.atomic
    @action(detail=True, methods=['post', 'delete'])
    def accept(self, request: Request, pk) -> Response:
        experience: Experience = self.get_object()
        if request.method == 'POST':
            try:
                if request.user.accepted_experiences.filter(pk=experience.pk).exists():
                    return Response('User cannot accept twice', status=status.HTTP_400_BAD_REQUEST)
                request.user.accepted_experiences.add(experience)
                experience.calc_total_accepts(set_and_save=True)
                if experience.created_by is not None and experience.created_by != request.user:
                    activity = Activity(
                        type=ActivityType.ACCEPTED_EXPERIENCE,
                        user=experience.created_by,
                        related_user=request.user,
                        experience=experience,
                        is_push=experience.created_by.activity_push_pref and experience.created_by.accept_complete_push_pref)
                    activity.save()
                    # Client wants to hide the fact that accepting happens before completing for now
                    # try:
                    #     if activity.is_push:
                    #         fb_service = FirebaseService()
                    #         fb_service.push_activity_to_user(activity)
                    # except Exception as e:
                    #     logger = logging.getLogger('app')
                    #     logger.info('Error sending comment notification')
            except Exception as e:
                transaction.set_rollback(rollback=True)
                raise e
            return Response()
        elif request.method == 'DELETE':
            request.user.accepted_experiences.remove(pk)
            experience.calc_total_accepts(set_and_save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)
        raise Exception('Not a valid method')

    @action(detail=True, methods=['post', 'delete'])
    def save(self, request: Request, pk) -> Response:
        if request.method == 'POST':
            request.user.saved_experiences.add(pk)
            return Response()
        else:
            request.user.saved_experiences.remove(pk)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'])
    def save_to_bucket_list(self, request: Request, pk) -> Response:
        if request.method == 'POST':
            request.user.bucket_list.add(pk)
            return Response()
        else:
            request.user.bucket_list.remove(pk)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def complete(self, request: Request, pk) -> Response:
        user: User = request.user
        validation_serializer = CompletionSerializer(data=request.data,
            context=self.get_serializer_context())
        validation_serializer.is_valid(raise_exception=True)
        validated_data = validation_serializer.validated_data
        experience: Experience = self.get_object()

        if user.completed_experiences.filter(id=pk).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Auto add the experience to the user added for now
        user.accepted_experiences.add(experience)
        experience.calc_total_accepts(set_and_save=True)

        # offset = validated_data['minutes_offset']
        # if not experience.valid_completion_time(offset):
        #     return Response(status=status.HTTP_400_BAD_REQUEST)
        completion = ExperienceCompletion(user=user, experience_id=pk)
        completion.save()
        if experience.categories and user.life_frame_id:
            lf_category_service = LifeFrameCategoryService()
            try:
                lf_category_service.record_activity(
                    lifeframe_id=user.life_frame_id,
                    categories=experience.categories)
            except Exception as e:
                logger = logging.getLogger('app')
                logger.info(str(e))
        try:
            if experience.created_by is not None and experience.created_by != request.user:
                activity = Activity(
                    type=ActivityType.COMPLETED_EXPERIENCE,
                    user=experience.created_by,
                    related_user=request.user,
                    experience=experience,
                    is_push=experience.created_by.activity_push_pref and experience.created_by.accept_complete_push_pref)
                activity.save()
                # Send notification to experience creator
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
                experience_completion=completion,
                experience_id=pk,)
            post.save()
            activities = []
            for mention in post.mentions.all():
                activities.append(Activity(
                    type=ActivityType.MENTIONED_POST,
                    user=mention,
                    related_user=request.user,
                    post=post,
                    is_push=post.created_by.activity_push_pref and post.created_by.mention_push_pref))
            Activity.objects.bulk_create(activities)
            try:
                fb_service = FirebaseService()
                for a in activities:
                    if not a.is_push:
                        continue
                    fb_service.push_activity_to_user(a)
            except Exception as e:
                logger = logging.getLogger('app')
                logger.info('Error sending experience completion post mention notification')
        except Exception as e:
            transaction.set_rollback(rollback=True)
            raise e

        return_serializer = self.get_serializer(post)
        return Response(return_serializer.data, status=status.HTTP_201_CREATED)

    # DELETE /experiences/{id}/
    def destroy(self, request: Request, pk) -> Response:
        request_user: User = request.user
        experience: Experience = self.get_object()
        if experience.created_by != request_user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        experience.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
