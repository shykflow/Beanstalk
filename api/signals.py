import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from api.models import (
    Experience,
)
from api.utils import update_experience_latlong_one_to_one_ref

logger = logging.getLogger('app')

# method for updating
@receiver(post_save, sender=Experience, dispatch_uid="post_save_update_experience_latlong_one_to_one_ref")
def post_save_update_experience_latlong_one_to_one_ref(sender, created, instance: Experience, **kwargs):
    update_experience_latlong_one_to_one_ref(experience=instance)