from django.db.models import (
    CASCADE,
    ForeignKey,
)

from sponsorship.models.abstract import Sponsorship


class PlaylistSponsorship(Sponsorship):
    playlist = ForeignKey('api.Playlist', on_delete=CASCADE, related_name='sponsorships')

