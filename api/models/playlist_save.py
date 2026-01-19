from django.db import models

class PlaylistSave(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='playlist_saves')
    created_at = models.DateTimeField(auto_now_add=True)
    playlist = models.ForeignKey('Playlist', on_delete=models.CASCADE)
