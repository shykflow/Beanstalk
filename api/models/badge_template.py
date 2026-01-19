from django.db import models


class BadgeTemplate(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=1000)
    photo = models.ImageField(upload_to='badges', max_length=1000)
    category = models.IntegerField(blank=True, null=True, help_text='LifeFrame ID')
