from django.db import models


class Interest(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    category = models.IntegerField(help_text='LifeFrame ID')
