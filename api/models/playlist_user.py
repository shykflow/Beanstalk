from django.db import models


class PlaylistUser(models.Model):
    """
    Followers AND Editors, will reuse this table for both roles
    """
    editor = models.BooleanField(default=False)
    playlist = models.ForeignKey('Playlist', on_delete=models.CASCADE)
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    allowed_to_add = models.IntegerField(default=0)
    num_added = models.IntegerField(default=0)
    # Needs review, should this be a separate record for showing on the action page?
    action_page_visible = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
