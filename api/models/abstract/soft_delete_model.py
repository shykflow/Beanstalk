import datetime
from django.db import models


class SoftDeleteManager(models.Manager):
    """
    Inherit from this class to add soft delete functionality to a model.
    If used in the admin panel, make sure that class inherits from
    `SoftDeleteModelAdmin`.
    """

    use_for_related_fields = True
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def restore(self):
        """Un-soft delete"""
        self.deleted_at = None
        self.is_deleted = False
        self.save()

    # override
    def delete(self, *args, **kwargs):
        """Soft delete"""
        self.deleted_at = datetime.datetime.now(tz=datetime.timezone.utc)
        self.is_deleted = True
        self.save()

    class Meta:
        abstract = True
