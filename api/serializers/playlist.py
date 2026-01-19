from rest_framework import serializers
from django.db.models import Count

from api.models import (
    Playlist,
    PlaylistCostRating,
    PlaylistStarRating,
)
from api.serializers.comment import CommentSerializer
from api.serializers.user import UserViewSerializer
from api.utils.measure_time_diff import MeasureTimeDiff


class PlaylistValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Playlist
        extra_kwargs = {
            'created_by': {
                'default': serializers.CurrentUserDefault(),
            }
        }
        fields = (
            'id',
            'name',
            'description',
            'editability',
            'visibility',
            'start',
            'end',
            'created_by',
            'start_time',
            'end_time',
            'start_time_date_only',
            'end_time_date_only',
            'use_local_time',
        )


class PlaylistViewSerializer(serializers.ModelSerializer):
    verbose_timing=False

    def __init__(
        self,
        instance,
        num_sample_comments: int=0,
        include_experience_ids: bool=False,
        *args,
        **kwargs):
        """Total comments and total accepts are opt in,
        average star rating is opt out"""
        self.num_sample_comments = num_sample_comments
        self.include_experience_ids = include_experience_ids
        super().__init__(instance, *args, **kwargs)
        if self.context.get('request') is None:
            raise Exception('Request not in context')

    created_by = UserViewSerializer(read_only=True)
    accepted_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True)
    experience_ids = serializers.SerializerMethodField()
    mentions = serializers.SerializerMethodField()
    model = serializers.SerializerMethodField()
    num_completed_experiences = serializers.SerializerMethodField()
    num_experiences = serializers.SerializerMethodField()
    has_comments = serializers.SerializerMethodField()
    sample_comments = serializers.SerializerMethodField()
    user_accepted = serializers.SerializerMethodField()
    user_complete = serializers.SerializerMethodField()
    user_like = serializers.SerializerMethodField()
    user_star_rating = serializers.SerializerMethodField()

    def get_num_experiences(self, playlist: Playlist) -> int | None:
        with MeasureTimeDiff(
            label='PlaylistViewSerializer - get_num_experiences',
            enabled=PlaylistViewSerializer.verbose_timing,
            depth=3):
            request = self.context.get('request')
            return playlist.experiences \
                .exclude(created_by__in = request.user.blocks.all()) \
                .exclude(created_by__blocks=request.user) \
                .count()

    def get_num_completed_experiences(self, playlist: Playlist) -> int | None:
        request = self.context.get('request')
        with MeasureTimeDiff(
            label='PlaylistViewSerializer - get_num_completed_experiences',
            enabled=PlaylistViewSerializer.verbose_timing,
            depth=3):
            return playlist.experiences \
                .filter(users_completed=request.user) \
                .exclude(created_by__in = request.user.blocks.all()) \
                .exclude(created_by__blocks=request.user) \
                .count()

    def get_mentions(self, playlist: Playlist) -> list[dict]:
        # use prefetch_related on querysets to make this faster
        with MeasureTimeDiff(
            label='PlaylistViewSerializer - get_mentions',
            enabled=PlaylistViewSerializer.verbose_timing,
            depth=3):
            mentioned_users = list(m for m in playlist.mentions.all())
            dicts = [
                { 'user_id': m.id, 'username': m.username }
                for m in mentioned_users
            ]
            return dicts

    def get_model(self, playlist: Playlist) -> str:
        return 'Playlist'

    def get_has_comments(self, playlist: Playlist) -> bool:
        return playlist.total_comments > 0

    def get_sample_comments(self, playlist: Playlist) -> list[map] :
        if self.num_sample_comments == 0:
            return []
        with MeasureTimeDiff(
            label='PlaylistViewSerializer - get_sample_comments',
            enabled=PlaylistViewSerializer.verbose_timing,
            depth=3):
            comments = playlist.comments \
                .filter(parent=None) \
                .annotate(like_count=Count('likes')) \
                .order_by('-like_count', '-created_at') \
                [:self.num_sample_comments]
            request_context = {'request':  self.context.get('request')}
            serializer = CommentSerializer(
                comments,
                context=request_context,
                many=True)
            return serializer.data

    def get_user_accepted(self, playlist: Playlist) -> bool:
        with MeasureTimeDiff(
            label='PlaylistViewSerializer - get_user_accepted',
            enabled=PlaylistViewSerializer.verbose_timing,
            depth=3):
            request = self.context.get('request')
            return request.user.accepted_playlists \
                .filter(pk=playlist.pk) \
                .exists()

    def get_user_complete(self, playlist: Playlist) -> bool:
        with MeasureTimeDiff(
            label='PlaylistViewSerializer - get_user_complete',
            enabled=PlaylistViewSerializer.verbose_timing,
            depth=3):
            request = self.context.get('request')
            return request.user.completed_playlists \
                .filter(pk=playlist.pk) \
                .exists()

    def get_user_like(self, playlist: Playlist) -> bool:
        with MeasureTimeDiff(
            label='PlaylistViewSerializer - get_user_like',
            enabled=PlaylistViewSerializer.verbose_timing,
            depth=3):
            request = self.context.get('request')
            return playlist.likes \
                .filter(pk=request.user.pk) \
                .exists()

    def get_user_star_rating(self, playlist: Playlist) -> int | None:
        with MeasureTimeDiff(
            label='PlaylistViewSerializer - get_user_star_rating',
            enabled=PlaylistViewSerializer.verbose_timing,
            depth=3):
            request = self.context.get('request')
            rating: PlaylistStarRating = PlaylistStarRating.objects \
                .filter(playlist=playlist, created_by=request.user) \
                .first()
            if rating is None:
                return None
            return rating.rating

    def get_experience_ids(self, playlist: Playlist) -> list | None:
        if not self.include_experience_ids:
            return None
        with MeasureTimeDiff(
            label='PlaylistViewSerializer - get_experience_ids',
            enabled=PlaylistViewSerializer.verbose_timing,
            depth=3):
            ids = playlist.experiences.values_list('id', flat=True)
            return list(ids)

    class Meta:
        model = Playlist
        fields = (
            'id',
            'name',
            'description',
            'created_at',
            'accepted_at',
            'completed_at',
            'editability',
            'visibility',
            'start',
            'end',
            'video',
            'highlight_image',
            'highlight_image_thumbnail',
            'created_by',
            'start_time',
            'end_time',
            'start_time_date_only',
            'end_time_date_only',
            'use_local_time',
            'total_completes',
            'total_likes',
            'num_experiences',
            'num_completed_experiences',
            'average_star_rating',
            'mentions',
            'model',
            'total_comments',
            'has_comments',
            'sample_comments',
            'user_accepted',
            'user_complete',
            'user_like',
            'user_star_rating',
            'experience_ids',

            # aggregates
            'average_cost_rating',
            'average_star_rating',
            'total_accepts',
            'total_comments',
            'total_completes',
            'total_likes',
            'total_reviews',
        )


class PlaylistDetailSerializer(PlaylistViewSerializer):

    user_cost_rating = serializers.SerializerMethodField()
    user_saved = serializers.SerializerMethodField()

    def get_user_cost_rating(self, playlist: Playlist) -> int | None:
        request = self.context.get('request')
        rating: PlaylistCostRating = PlaylistCostRating.objects \
            .filter(playlist=playlist, created_by=request.user) \
            .first()
        if rating is None:
            return None
        return rating.rating

    def get_user_saved(self, playlist: Playlist) -> bool:
        request = self.context.get('request')
        return request.user.saved_playlists \
            .filter(pk=playlist.pk) \
            .exists()

    class Meta:
        model = Playlist
        fields = PlaylistViewSerializer.Meta.fields + (
            'user_cost_rating',
            'user_saved',
        )
