from django.db import models


class Showcase(models.Model):
    user = models.OneToOneField('User', primary_key=True, on_delete=models.CASCADE)
