from io import BytesIO
from pathlib import PosixPath
from PIL import Image
from uuid import uuid4

from django.conf import settings
from django.core.files.base import File
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db import models

from api.enums import AttachmentType
from api.models.abstract.soft_delete_model import SoftDeleteModel
from api.utils import file_handling


class Attachment(SoftDeleteModel):
    name = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=1000, null=True, blank=True)
    file = models.FileField(upload_to='attachments', max_length=1000)
    thumbnail = models.ImageField(upload_to='attachments', max_length=1000, blank=True, null=True)
    type = models.PositiveSmallIntegerField(choices=AttachmentType.choices)
    sequence = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    playlist = models.ForeignKey('Playlist', on_delete=models.CASCADE, blank=True, null=True, related_name='attachments')
    experience = models.ForeignKey('Experience', on_delete=models.CASCADE, blank=True, null=True, related_name='attachments')
    experience_completion = models.ForeignKey('ExperienceCompletion', on_delete=models.CASCADE, blank=True, null=True, related_name='attachments')
    post = models.ForeignKey('Post', on_delete=models.CASCADE, blank=True, null=True, related_name='attachments')


    def generate_thumbnail_from_video(self,
        video_info: dict[str, float| int] | None = None, save: bool = False):
        if not type(self.file.file) is TemporaryUploadedFile:
            raise TypeError('self.file.file must be a TemporaryUploadedFile')
        if video_info is None:
            video_info = file_handling.get_video_info(input_path)
        input_path = self.file.file.temporary_file_path()
        temp_dir = PosixPath('/tmp')
        if not temp_dir.exists():
            raise Exception('/tmp directory could not be found')
        file_type = 'JPEG'
        screenshot_path: PosixPath = temp_dir / f'{uuid4()}.{file_type}'
        width = video_info.width
        height = video_info['height']
        larger_dimension = max(width, height)
        max_allowed_dimension = settings.FILE_UPLOADS['ATTACHMENTS']['THUMBNAIL_COMPRESS_TO_DIMENSION']['IMAGE']
        if larger_dimension > max_allowed_dimension:
            scale_down_factor = larger_dimension / max_allowed_dimension
            width = int(width / scale_down_factor)
            height = int(height / scale_down_factor)
        file_handling.take_screenshot(
            input_path,
            seconds=video_info['duration'] / 3,
            output_path=screenshot_path,
            scale=f'{width}x{height}'
        )
        with Image.open(screenshot_path) as thumbnail:
            blob = BytesIO()
            thumbnail.save(blob, file_type, optimize=True, quality=60)
            thumb_from_blob = File(blob)
            self.thumbnail.save(
                f'{uuid4()}.{file_type}',
                thumb_from_blob,
                save=save
            )
        screenshot_path.unlink()
