from django.db import models


class PowerProfileAdmin(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    can_control_children = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
