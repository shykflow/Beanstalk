from django.db import models

from api.enums import Publicity


class EarnedBadge(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    badge = models.ForeignKey('Badge', on_delete=models.CASCADE)
    experience = models.ForeignKey('Experience', on_delete=models.CASCADE, blank=True, null=True)
    experience_stack = models.ForeignKey('ExperienceStack', on_delete=models.CASCADE, blank=True, null=True)
    milestone = models.ForeignKey('Milestone', on_delete=models.CASCADE, blank=True, null=True)
    visibility = models.PositiveSmallIntegerField(choices=Publicity.choices, default=Publicity.PUBLIC)
    created_at = models.DateTimeField(auto_now_add=True)
