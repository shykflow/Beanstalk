from typing import Iterable, Optional
from django.db.models import (
    CASCADE,
    DateTimeField,
    ForeignKey,
    Model,
    PositiveSmallIntegerField,
)
from django.core.validators import MaxValueValidator, MinValueValidator


class CostRating(Model):
    class Meta:
        abstract = True
    rating = PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(4)])
    created_at = DateTimeField(auto_now_add=True)


class ExperienceCostRating(CostRating):
    experience = ForeignKey('Experience', on_delete=CASCADE)
    created_by = ForeignKey('User', on_delete=CASCADE, related_name='experience_cost_rating_users')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from api.models import Experience
        exp: Experience = self.experience
        exp.calc_average_cost_rating(set_and_save=True)
        exp.calc_total_reviews(set_and_save=True)

    def delete(self, *args, **kwargs):
        from api.models import Experience
        exp: Experience = self.experience
        super_save_value = super().delete(*args, **kwargs)
        if exp is not None:
            exp.calc_average_cost_rating(set_and_save=True)
            exp.calc_total_reviews(set_and_save=True)
        return super_save_value


class PlaylistCostRating(CostRating):
    playlist = ForeignKey('Playlist', on_delete=CASCADE)
    created_by = ForeignKey('User', on_delete=CASCADE, related_name='playlist_cost_rating_users')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from api.models import Playlist
        pl: Playlist = self.playlist
        pl.calc_average_cost_rating(set_and_save=True)
        pl.calc_total_reviews(set_and_save=True)

    def delete(self, *args, **kwargs):
        from api.models import Playlist
        pl: Playlist = self.playlist
        super_save_value = super().delete(*args, **kwargs)
        if pl is not None:
            pl.calc_average_cost_rating(set_and_save=True)
            pl.calc_total_reviews(set_and_save=True)
        return super_save_value
