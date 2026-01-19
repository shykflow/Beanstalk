from django.db import models

class ExperienceCompletion(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='completion_users')
    created_at = models.DateTimeField(auto_now_add=True)
    experience = models.ForeignKey('Experience', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from api.models import Experience
        exp: Experience = self.experience
        exp.calc_total_completes(set_and_save=True)

    def delete(self, *args, **kwargs):
        from api.models import Experience
        exp: Experience = self.experience
        super_save_value = super().delete(*args, **kwargs)
        exp.calc_total_comments(set_and_save=True)
        return super_save_value
