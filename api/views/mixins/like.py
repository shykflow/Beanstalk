import logging
from django.forms import BooleanField
from django.http import Http404
from django.db import transaction
from django.db.models import BooleanField, Case, Value, When
from django.db.models.query import QuerySet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from api.pagination import AppPageNumberPagination, get_page_size_from_request
from api.enums import ActivityType
from api.models import (
    Playlist,
    Experience,
    Comment,
    Like,
    Post,
    User,
    Activity,
)
from api.serializers.user import UserViewSerializer
from lf_service.category import LifeFrameCategoryService

class LikeMixin:

    @transaction.atomic
    @action(detail=True, methods=['post', 'get', 'delete'])
    def like(self, request: Request, pk) -> Response:
        user: User = request.user
        instance: Playlist | Experience | Comment | Post = self.get_object()
        user_liked = instance.likes.filter(pk=user.pk).exists()
        if request.method == 'POST':
            if user_liked:
                return Response('User cannot like twice', status=status.HTTP_400_BAD_REQUEST)
            instance.likes.add(user)
            instance.calc_total_likes(set_and_save=True)
            if type(instance) is Experience and instance.categories and user.life_frame_id:
                lf_category_service = LifeFrameCategoryService()
                try:
                    lf_category_service.record_activity(
                        lifeframe_id=user.life_frame_id,
                        categories=instance.categories)
                except Exception as e:
                    logger = logging.getLogger('app')
                    logger.info(str(e))
            if instance.created_by is not None and instance.created_by != user:
                activity = Activity(
                    user=instance.created_by,
                    related_user=request.user,
                    is_push = instance.created_by.activity_push_pref and instance.created_by.like_push_pref)
                match instance:
                    case Post():
                        activity.post = instance
                        activity.type = ActivityType.LIKED_POST
                    case Experience():
                        activity.experience = instance
                        activity.type = ActivityType.LIKED_EXPERIENCE
                    case Playlist():
                        activity.playlist=instance
                        activity.type=ActivityType.LIKED_PLAYLIST
                    case Comment():
                        activity.comment=instance
                        activity.type=ActivityType.LIKED_COMMENT
                        activity.related_comment = instance.parent
                        activity.playlist = instance.playlist
                        activity.experience = instance.experience
                        activity.post = instance.post
                try:
                    activity.save()
                except Exception as e:
                    transaction.set_rollback(True)
                    raise e
            return Response(status=status.HTTP_201_CREATED)
        if request.method == 'GET':
            return Response(user_liked)
        if not user_liked:
            raise Http404
        instance.likes.remove(user)
        if type(instance) == Experience:
            instance.calc_total_likes(set_and_save=True)
        activity_qs = Activity.objects.filter(user=instance.created_by, related_user=user)
        match instance:
            case Post():
                activity_qs = activity_qs.filter(
                    post=instance, type=ActivityType.LIKED_POST)
            case Experience():
                activity_qs = activity_qs.filter(
                    experience=instance, type=ActivityType.LIKED_EXPERIENCE)
            case Playlist():
                activity_qs = activity_qs.filter(
                    playlist=instance, type=ActivityType.LIKED_PLAYLIST)
            case Comment():
                activity_qs = activity_qs.filter(
                    comment=instance, type=ActivityType.LIKED_COMMENT)
        activity_qs.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic
    @action(detail=True, methods=['get'])
    def liking_users(self, request: Request, pk) -> Response:
        instance: Playlist | Experience | Comment | Post = self.get_object()
        qs: QuerySet
        # Query's like this enables ordering reverse chronologically of like creation.
        match instance:
            case Playlist():
                qs = Like.objects.filter(playlist=instance.id)
            case Experience():
                qs = Like.objects.filter(experience=instance.id)
            case Comment():
                qs = Like.objects.filter(comment=instance.id)
            case Post():
                qs = Like.objects.filter(post=instance.id)
        qs = qs.order_by('-created_at') \
            .prefetch_related('created_by')

        page_size = get_page_size_from_request(request, 20)
        paginator = AppPageNumberPagination(page_size=page_size)
        user_likes_page = paginator.paginate_queryset(qs, request)
        user_ids = [user_like.created_by.id for user_like in user_likes_page]
        users = User.objects.filter(id__in=user_ids) \
            .annotate(followed_by_viewer = Case(
                    When(id__in=request.user.follows.all(),
                        then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()))

        user_dict = dict([(user.id, user) for user in users])
        ordered_users = [
            user_dict.get(id)
            for id in user_ids
            if id in user_dict]

        context = {'request': request,}
        return_serializer = UserViewSerializer(ordered_users, many=True, context=context)
        return paginator.get_paginated_response(return_serializer.data)
