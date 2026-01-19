from django.core.cache import cache
from django.utils import timezone
from rest_framework import serializers

from api.models import (
    CategoryMapping,
)
from api.serializers.sponsorship import CategorySponsorshipViewSerializer
from api.utils.categories import CategoryContentQuerysets
from sponsorship.models import (
    CategorySponsorship,
)

class CategoryMappingSerializer(serializers.ModelSerializer):

    sponsorship = serializers.SerializerMethodField()
    def get_sponsorship(self, cm: CategoryMapping):
        sponsorship: CategorySponsorship = cm.sponsorship
        if sponsorship is None:
            return None
        if cm.category_id != sponsorship.category_id:
            return None
        now = timezone.datetime.now(tz=timezone.utc)
        expires_at = sponsorship.expires_at
        if expires_at is not None and expires_at < now:
            return None
        serializer = CategorySponsorshipViewSerializer(sponsorship, many=False)
        return serializer.data

    model = serializers.SerializerMethodField()
    def get_model(self, _: CategoryMapping):
        return 'CategoryMapping'

    name = serializers.SerializerMethodField()
    def get_name(self, m: CategoryMapping):
        return m.get_name()

    parent_id = serializers.SerializerMethodField()
    def get_parent_id(self, m: CategoryMapping):
        if hasattr(m, 'parent_id'):
            return m.parent_id
        return None

    parent_name = serializers.SerializerMethodField()
    def get_parent_name(self, m: CategoryMapping):
        if hasattr(m, 'parent_name'):
            return m.parent_name
        return None

    experience_count = serializers.SerializerMethodField()
    def get_experience_count(self, m: CategoryMapping):
        if self.context == None:
            return None
        with_related_counts = self.context.get('with_related_counts', False)
        if not with_related_counts:
            return None
        cache_key = f'category|{m.category_id}|experience_count'
        count = cache.get(cache_key, None)
        if count is None or count == 0:
            count = CategoryContentQuerysets \
                .experiences_qs(m.category_id) \
                .count()
            cache.set(
                key=cache_key,
                value=count,
                timeout=300) # 5 minutes
        return count

    playlist_count = serializers.SerializerMethodField()
    def get_playlist_count(self, m: CategoryMapping):
        if self.context == None:
            return None
        with_related_counts = self.context.get('with_related_counts', False)
        if not with_related_counts:
            return None
        cache_key = f'category|{m.category_id}|playlist_count'
        count = cache.get(cache_key, None)
        if count is None or count == 0:
            count = CategoryContentQuerysets \
                .playlists_qs(m.category_id) \
                .count()
            cache.set(
                key=cache_key,
                value=count,
                timeout=300) # 5 minutes
        return count

    post_count = serializers.SerializerMethodField()
    def get_post_count(self, m: CategoryMapping):
        if self.context == None:
            return None
        with_related_counts = self.context.get('with_related_counts', False)
        if not with_related_counts:
            return None
        cache_key = f'category|{m.category_id}|post_count'
        count = cache.get(cache_key, None)
        if count is None or count == 0:
            count = CategoryContentQuerysets \
                .posts_qs(m.category_id) \
                .count()
            cache.set(
                key=cache_key,
                value=count,
                timeout=300) # 5 minutes
        return count

    class Meta:
        model = CategoryMapping
        fields = (
            'id',
            'model',
            'name',
            'category_id',
            'parent_id',
            'parent_name',
            'show_in_picker',
            'picker_sequence',
            'image',
            'overlay_opacity',
            'text_color',
            'background_color',
            'experience_count',
            'playlist_count',
            'post_count',
            'sponsorship',
            'details',
        )
