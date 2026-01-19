from django.db.models import (
    CASCADE,
    ForeignKey,
)
from sponsorship.models.abstract import Sponsorship


class ExperienceSponsorship(Sponsorship):
    experience = ForeignKey('api.Experience', on_delete=CASCADE, related_name='sponsorships')

