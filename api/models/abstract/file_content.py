from uuid import uuid4

from django.db import models

from api.utils import file_handling
from api.validators import is_uuid4


class FileContent(models.Model):
    class Meta:
        abstract = True

    # Django stores filefields as empty strings no matter what. null=true adds ambiguity,
    # where queries could be empty string or null.
    video = models.FileField(
        upload_to='file_uploads',
        blank=True,
        max_length=1000,
        db_index=True)
    highlight_image = models.ImageField(
        upload_to='file_uploads',
        blank=True, max_length=1000,
        db_index=True)
    highlight_image_thumbnail = models.ImageField(
        upload_to='file_uploads',
        blank=True,
        max_length=1000)

    # override
    def save(self, *args, **kwargs):
        """Enforce unique names for `video` and `highlight_image`.
        `highlight_image_thumbnail` is skipped since it is auto-generated."""
        if bool(self.video):
            video_url = file_handling.split_file_url(self.video.name)
            if not is_uuid4(video_url['name']):
                self.video.name = f"{uuid4()}.{video_url['extension']}"
        if bool(self.highlight_image):
            highlight_image_url = file_handling.split_file_url(self.highlight_image.name)
            if not is_uuid4(highlight_image_url['name']):
                self.highlight_image.name = f"{uuid4()}.{highlight_image_url['extension']}"
        super().save(*args, **kwargs)
