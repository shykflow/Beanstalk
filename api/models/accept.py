from django.db import models


class Accept(models.Model):
    class Meta:
        abstract = True
    created_at = models.DateTimeField(auto_now_add=True)


class PlaylistAccept(Accept):
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='playlist_users_accepted')
    playlist = models.ForeignKey(
        'Playlist',
        on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from api.models import Playlist
        pl: Playlist = self.playlist
        pl.calc_total_accepts(set_and_save=True)

    def delete(self, *args, **kwargs):
        from api.models import Playlist
        pl: Playlist = self.playlist
        super_save_value = super().delete(*args, **kwargs)
        pl.calc_total_comments(set_and_save=True)
        return super_save_value


class ExperienceAccept(Accept):
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='experience_users_accepted')
    experience = models.ForeignKey(
        'Experience',
        on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from api.models import Experience
        exp: Experience = self.experience
        exp.calc_total_accepts(set_and_save=True)

    def delete(self, *args, **kwargs):
        from api.models import Experience
        exp: Experience = self.experience
        super_save_value = super().delete(*args, **kwargs)
        exp.calc_total_comments(set_and_save=True)
        return super_save_value
