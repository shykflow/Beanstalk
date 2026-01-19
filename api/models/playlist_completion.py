from django.db import models

class PlaylistCompletion(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='playlist_completions')
    created_at = models.DateTimeField(auto_now_add=True)
    playlist = models.ForeignKey('Playlist', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from api.models import Playlist
        pl: Playlist = self.playlist
        pl.calc_total_completes(set_and_save=True)

    def delete(self, *args, **kwargs):
        from api.models import Playlist
        pl: Playlist = self.playlist
        super_save_value = super().delete(*args, **kwargs)
        pl.calc_total_comments(set_and_save=True)
        return super_save_value
