from django.db import models

class SavePersonalBucketList(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='bucket_list_saves')
    created_at = models.DateTimeField(auto_now_add=True)
    experience = models.ForeignKey('Experience', on_delete=models.CASCADE)
