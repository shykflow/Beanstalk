from django.db import models
import uuid

class PlaylistPin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='playlist_pins')
    created_at = models.DateTimeField(auto_now_add=True)
    position = models.PositiveSmallIntegerField()
    playlist = models.ForeignKey('Playlist', on_delete=models.CASCADE)

