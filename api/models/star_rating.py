from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class StarRating(models.Model):
    class Meta:
        abstract = True
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ])
    created_at = models.DateTimeField(auto_now_add=True)


class ExperienceStarRating(StarRating):
    experience = models.ForeignKey(
        'Experience',
        on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='experience_star_ratings_users')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from api.models import Experience
        exp: Experience = self.experience
        exp.calc_average_star_rating(set_and_save=True)
        exp.calc_total_reviews(set_and_save=True)

    def delete(self, *args, **kwargs):
        from api.models import Experience
        exp: Experience = self.experience
        super_save_value = super().delete(*args, **kwargs)
        if exp is not None:
            exp.calc_average_star_rating(set_and_save=True)
            exp.calc_total_reviews(set_and_save=True)
        return super_save_value


class PlaylistStarRating(StarRating):
    playlist = models.ForeignKey(
        'Playlist',
        on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='playlist_star_ratings_users')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from api.models import Playlist
        pl: Playlist = self.playlist
        pl.calc_average_star_rating(set_and_save=True)
        pl.calc_total_reviews(set_and_save=True)

    def delete(self, *args, **kwargs):
        from api.models import Playlist
        pl: Playlist = self.playlist
        super_save_value = super().delete(*args, **kwargs)
        if pl is not None:
            pl.calc_average_star_rating(set_and_save=True)
            pl.calc_total_reviews(set_and_save=True)
        return super_save_value
