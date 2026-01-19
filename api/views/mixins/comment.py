import logging
from django.db import transaction
from django.db.models import (
    Count,
    QuerySet,
)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request

from api.enums import ActivityType
from api.models import (
    Activity,
    Playlist,
    Experience,
    Comment,
    Like,
    Post,
    Like,
    User,
)

from api.serializers.comment import CommentSerializer
from api.pagination import AppPageNumberPagination
from api.services.firebase import FirebaseService

class CommentMixin:

    @action(detail=True, methods=['get'], pagination_class=AppPageNumberPagination)
    def comments(self, request: Request, pk):
        user: User = request.user
        instance: Playlist | Experience | Comment | Post = self.get_object()
        comments = instance.comments.all() \
            .exclude(created_by__in=user.blocks.all()) \
            .exclude(created_by__blocks=user) \
            .exclude(parent__created_by__in=user.blocks.all()) \
            .exclude(parent__created_by__blocks=user) \
            .prefetch_related('created_by', 'mentions') \
            .order_by('created_at', '-id')
        if type(instance) is not Comment:
            comments = comments.filter(parent=None)

        page = self.paginate_queryset(comments)
        user_likes: QuerySet[Like] = Comment.likes.through.objects.filter(
            created_by=user,
            comment__in=page)
        serializer = CommentSerializer(page, many=True, context={
            'request': request,
            'user_likes': user_likes,
        })
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'])
    def sample_comments(self, request: Request, pk):
        instance: Playlist | Experience | Comment | Post = self.get_object()
        comments = instance.comments \
            .filter(parent=None) \
            .annotate(like_count=Count('likes')) \
            .order_by('-like_count', '-created_at') \
            [:2]
        request_context = {'request': request}
        serializer = CommentSerializer(
            comments,
            context=request_context,
            many=True)
        return Response(serializer.data)

    @transaction.atomic
    @action(detail=True, methods=['delete', 'post', 'put'])
    def comment(self, request, pk):
        user: User = request.user
        instance: Playlist | Experience | Comment | Post = self.get_object()
        data = request.data
        if request.method == 'POST':
            activityType: ActivityType
            match instance:
                case Playlist():
                    activityType = ActivityType.COMMENTED_PLAYLIST
                    data['playlist'] = instance.id
                case Experience():
                    activityType = ActivityType.COMMENTED_EXPERIENCE
                    data['experience'] = instance.id
                case Comment():
                    activityType = ActivityType.COMMENTED_COMMENT
                    if instance.parent is not None:
                        return Response(
                            'Cannot create child comment of comment with parent',
                            status=status.HTTP_400_BAD_REQUEST)
                    data['parent'] = instance.id
                    if instance.playlist is not None:
                        data['playlist'] = instance.playlist.id
                    if instance.experience is not None:
                        data['experience'] = instance.experience.id
                    if instance.post is not None:
                        data['post'] = instance.post.id
                case Post():
                    activityType = ActivityType.COMMENTED_POST
                    data['post'] = instance.id
                case _:
                    raise Exception('Not a supported type')
            serializer = CommentSerializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            comment_activity: Activity
            mention_activities: list[Activity] = []
            try:
                comment_data = serializer.validated_data
                comment_data['created_by'] = user
                new_comment = Comment.objects.create(**comment_data)
                mentions_contain_creator = False
                for mention in new_comment.mentions.all():
                    if mention == user:
                        mentions_contain_creator = True
                    is_push = instance.created_by.activity_push_pref \
                        and instance.created_by.mention_push_pref
                    a = Activity(
                        type=ActivityType.MENTIONED_COMMENT,
                        user=mention,
                        related_user=user,
                        playlist=new_comment.playlist,
                        experience=new_comment.experience,
                        post=new_comment.post,
                        comment=new_comment.parent,
                        related_comment=new_comment,
                        is_push=is_push)
                    a.save()
                    mention_activities.append(a)

                # TODO If the creator of the top level content is mentioned, mark one the Activities as seen and non-push
                # based on what the creators preferences are.
                # Example:
                #    UserA(comment_push_pref: True, mention_push_pref: False)
                #    UserA creates Post
                #    UserB comments '@UserA nice post!'
                #    Activity(type: MENTIONED_COMMENT, is_push: False, seen: True)
                #    Activity(type: COMMENTED_POST, is_push: True, seen: False )
                if instance.created_by != user and not mentions_contain_creator:
                    # For comments of comments the original/parent comment is the one which needs the activity
                    # e.g "@billy commented on YOUR comment"
                    is_push = instance.created_by.activity_push_pref \
                        and instance.created_by.comment_push_pref
                    comment_activity = Activity(
                        type=activityType,
                        user=instance.created_by,
                        related_user=user,
                        comment=new_comment.parent,
                        related_comment=new_comment,
                        playlist=new_comment.playlist,
                        experience=new_comment.experience,
                        post=new_comment.post,
                        is_push=is_push)
                    comment_activity.save()
            except Exception as e:
                transaction.set_rollback(rollback=True)
                raise e
            try:
                fb_service = FirebaseService()
                for a in mention_activities:
                    if not a.is_push:
                        continue
                    fb_service.push_activity_to_user(a)
                if comment_activity.is_push:
                    fb_service.push_activity_to_user(comment_activity)
            except Exception as e:
                logger = logging.getLogger('app')
                logger.info('Error sending comment or comment mention notification')
            serializer = CommentSerializer(new_comment, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        try:
            comment_id = int(request.query_params.get('comment_id'))
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if type(instance) is Comment and instance.pk == comment_id:
            comment = instance
        else:
            comment = instance.comments.filter(pk=comment_id).first()
            if comment is None:
                return Response(status=status.HTTP_404_NOT_FOUND)
        if comment.created_by != user:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        if request.method == 'DELETE':
            comment.comments.delete()
            comment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = CommentSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        comment.text = data['text']
        comment.edited = True
        comment.save()
        return Response(data)
