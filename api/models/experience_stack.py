from django.db import models


class ExperienceStack(models.Model):
    name = models.CharField(max_length=500)
    description = models.CharField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    users_followed = models.ManyToManyField('User', related_name='followed_experience_stacks')
    experiences = models.ManyToManyField('Experience', related_name='experience_stacks')
