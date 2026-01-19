from django.db import models


class Badge(models.Model):
    """
    Plan to show the experience name, or playlist name, etc. if name is null.
    """
    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=1000, blank=True, null=True)
    photo = models.ImageField(upload_to='badges', max_length=1000)
