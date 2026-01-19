from django.db import models
from django.core.cache import cache


class CustomCategory(models.Model):
    class Meta:
        verbose_name_plural = 'Custom categories'

    name = models.CharField(max_length=200, db_index=True)
    needs_manual_review = models.BooleanField(default=False)

    @property
    def experience_count(self):
        cache_key = f'custom_category|{self.id}|experience_count'
        count = cache.get(cache_key, None)
        if count is None or count == 0:
            count = self.experiences.count()
            cache.set(
                key=cache_key,
                value=count,
                timeout=300) # 5 minutes
        return count

    @property
    def playlist_count(self):
        from api.models import Playlist
        cache_key = f'custom_category|{self.id}|playlist_count'
        count = cache.get(cache_key, None)
        if count is None or count == 0:
            playlist_qs = Playlist.objects \
                .filter(experiences__custom_categories__name__exact=self.name) \
                .filter(experiences__is_deleted=False)
            count = playlist_qs.count()
            cache.set(
                key=cache_key,
                value=count,
                timeout=300) # 5 minutes
        return count

    @property
    def post_count(self):
        return None
