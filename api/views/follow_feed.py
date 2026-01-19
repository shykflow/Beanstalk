from django.core.cache import cache
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from uuid import uuid4

from api.serializers.playlist import PlaylistViewSerializer
from api.serializers.experience import ExperienceViewSerializer
from api.serializers.post import PostViewSerializer
from api.utils.follow_feed import FollowContinuation
from api.models import (
    Playlist,
    Experience,
    Post,
    User,
)


class FollowFeedViewSet(viewsets.ViewSet):

    num_sample_comments = 2

    @transaction.atomic
    def list(self, request: Request, *args, **kwargs) -> Response:
        '''Any exception will revert the cache to how it was previously'''
        try:
            user: User = request.user
            caught_up = request.query_params.get('caught_up', 'false') == 'true'
            refresh = request.query_params.get('refresh', 'false') == 'true'
            continuation_key: str = request.query_params.get('continuation', '').strip()
            if continuation_key == '':
                continuation_key = uuid4()
            continuation = FollowContinuation(user=user, token=continuation_key, refresh=refresh)
            old_continuation_cache = continuation.get_cache()
            if not refresh:
                continuation.mark_seen()
            user_ids = list(User.objects
                .filter(pk__in=user.follows.all())
                .values_list('id', flat=True))
            user_ids.append(user.pk) # Comment out to remove seeing your own content

            seen: dict[str, QuerySet] = {
                'experiences': user.seen_experiences.all(),
                'playlists': user.seen_playlists.all(),
                'posts': user.seen_posts.all(),
            }

            if not caught_up:
                experiences = Experience.objects \
                    .filter(created_by__in=user_ids) \
                    .exclude(id__in=continuation.sent_experiences) \
                    .exclude(id__in=seen['experiences']) \
                    .order_by('-created_at', 'id')[:4] \
                    .prefetch_related('created_by', 'star_ratings', 'likes')

                playlists = Playlist.objects \
                    .filter(created_by__in=user_ids) \
                    .exclude(id__in=continuation.sent_playlists) \
                    .exclude(id__in=seen['playlists']) \
                    .order_by('-created_at', 'id')[:4] \
                    .prefetch_related('created_by', 'star_ratings', 'likes')

                posts = Post.objects \
                    .filter(created_by__in=user_ids) \
                    .exclude(id__in=continuation.sent_posts) \
                    .exclude(id__in=seen['posts']) \
                    .order_by('-created_at', 'id')[:4] \
                    .prefetch_related('created_by', 'likes')

            if caught_up or (
                not experiences.exists() and
                not playlists.exists() and
                not posts.exists()):

                experiences = seen['experiences'] \
                    .filter(created_by__in=user_ids) \
                    .exclude(id__in=continuation.sent_experiences) \
                    .order_by('-created_at', 'id')[:4] \
                    .prefetch_related(*[
                        'created_by',
                        'experience_star_ratings_users',
                        'likes',
                    ])

                playlists = seen['playlists'] \
                    .filter(created_by__in=user_ids) \
                    .exclude(id__in=continuation.sent_playlists) \
                    .order_by('-created_at', 'id')[:4] \
                    .prefetch_related(*[
                        'created_by',
                        'playlist_star_ratings_users',
                        'likes',
                    ])

                posts = seen['posts'] \
                    .filter(created_by__in=user_ids) \
                    .exclude(id__in=continuation.sent_posts) \
                    .order_by('-created_at', 'id')[:8] \
                    .prefetch_related(*[
                        'created_by',
                        'likes',
                    ])

                if not caught_up:
                    caught_up = True
                    continuation.mark_seen()

            data = {
                'continuation': continuation.token,
                'caught_up': caught_up,
                'experiences': [],
                'playlists': [],
                'posts': [],
            }

            request_context = {'request': request}

            serializer = ExperienceViewSerializer(
                experiences,
                many=True,
                num_sample_comments=self.num_sample_comments,
                context=request_context)
            exp_data = serializer.data
            data['experiences'] = exp_data
            continuation.sent_experiences += [c['id'] for c in exp_data]

            serializer = PlaylistViewSerializer(
                playlists,
                many=True,
                num_sample_comments=self.num_sample_comments,
                context=request_context)
            serialized_playlists = serializer.data
            data['playlists'] = serialized_playlists
            continuation.sent_playlists += [
                pl['id']
                for pl in serialized_playlists
            ]

            serializer = PostViewSerializer(
                posts,
                many=True,
                num_sample_comments=self.num_sample_comments,
                context=request_context)
            serialized_posts = serializer.data
            data['posts'] = serialized_posts
            continuation.sent_posts += [p['id'] for p in serialized_posts]

            continuation.set_cache()
            return Response(data)
        except Exception as e:
            cache.set(
                key=continuation.cache_key,
                value=old_continuation_cache,
                timeout=FollowContinuation.cache_timeout)
            raise e
