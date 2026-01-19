from django.db import models
from api.enums import BadgePlanType


class BadgePlan(models.Model):
    type = models.PositiveSmallIntegerField(choices=BadgePlanType.choices, default=BadgePlanType.COMPLETE_TO_EARN)
    earn_until = models.DateTimeField(help_text="For type ENDS_AT")
    earn_limit = models.IntegerField(null=True, blank=True, help_text="For type EARN_LIMIT")
    experience = models.ForeignKey('Experience', on_delete=models.CASCADE)
    badge = models.ForeignKey('Badge', on_delete=models.CASCADE)
