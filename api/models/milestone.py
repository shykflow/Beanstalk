from django.db import models


class Milestone(models.Model):
    codename = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.CharField(max_length=5000)
