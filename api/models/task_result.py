from django.db import models
from .user import User


class TaskResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task_id = models.CharField(max_length=255)
    text = models.CharField(max_length=500)
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    category_limit = models.IntegerField(default=0)
    description_limit = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.user} - {self.status}'
