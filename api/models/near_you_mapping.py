from django.db import models
from django.db.models import Q
from django.core.validators import MaxValueValidator, MinValueValidator
from django.template.defaultfilters import pluralize

from api.models.abstract.discover_mapping import DiscoverMapping
from api.validators import non_zero_validator


class NearYouMapping(DiscoverMapping):
    image = models.ImageField(upload_to='near_you', max_length=1000, blank=True, null=True)
    is_default = models.BooleanField(default=False, help_text="If checked, \
        this mapping will be used as a fallback if a user's location data is unavailable.\n \
        If multiple mappings are marked as default, only the first will be used.")
    # TODO: Convert the mapping's latitude / longitude to a PointField()
    latitude = models.FloatField(blank=True, null=True,
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
        help_text='The latitude of the center of the circle to which this mapping applies')
    longitude = models.FloatField(blank=True, null=True,
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
        help_text='The longitude of the center of the circle to which this mapping applies')
    radius = models.PositiveSmallIntegerField(blank=True, null=True,
        validators=[non_zero_validator],
        help_text='The radius in miles of the circle to which this mapping applies.')

    @property
    def _admin_preview_text(self) -> str:
        return 'NEAR YOU'

    def __str__(self):
        self_as_str = "(Default)" if self.is_default else ""
        if self.latitude is None and self.longitude is None:
            return self_as_str
        return f'{self_as_str} Center: ({self.latitude}°, {self.longitude}°)' \
            f' Radius: {self.radius} mile{pluralize(self.radius)}'

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                        Q(latitude__isnull=False) &
                        Q(longitude__isnull=False) &
                        Q(radius__isnull=False)
                    ) | (
                        Q(latitude__isnull=True) &
                        Q(longitude__isnull=True) &
                        Q(radius__isnull=True) &
                        Q(is_default=True)
                    ), name='must_be_default_if_latitude_or_longitude_or_radius_are_null'
            )
        ]
