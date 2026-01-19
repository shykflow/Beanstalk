from django.db import models

from django.db.models import Q, F, CheckConstraint
class UserBlock(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    blocked_user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='blocks_of_self')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'blocked_user',)
        constraints = (
            CheckConstraint(
                name="no_self_blocking",
                check=~Q(user=F('blocked_user'))),
            models.UniqueConstraint(
                name='no_duplicate_blocks',
                fields=['user', 'blocked_user']),
        )
