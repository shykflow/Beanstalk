from django.db import models
from django.db.models import Q, F, CheckConstraint


class UserFollow(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    followed_user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='follows_of_self')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = (
            CheckConstraint(
                name='no_self_following',
                check=~Q(user=F('followed_user'))),
            models.UniqueConstraint(
                name='no_duplicate_follows',
                fields=['user', 'followed_user']),
        )
