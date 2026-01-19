from io import BytesIO
import os
from pathlib import PosixPath
from PIL import Image, ImageOps
from uuid import uuid4
import wand.image as WandImage

from django.conf import settings
from django.core.files.base import File
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile
)
from django.core.exceptions import ValidationError

from api.models import (
    Post,
    Experience,
    Playlist,
)
from api.utils import file_handling


# InMemoryUploadedFile comes from small files
# TemporaryUploadedFile comes from big files
# https://docs.djangoproject.com/en/4.1/ref/files/uploads/#module-django.core.files.uploadhandler


class AppContentFileHandler:
    app_content: Post | Experience | Playlist

    _opened_video: InMemoryUploadedFile | TemporaryUploadedFile | None
    _opened_image: InMemoryUploadedFile | TemporaryUploadedFile | None
    _opened_thumb: InMemoryUploadedFile | TemporaryUploadedFile | None

    _video_info: file_handling.VideoInfo
    _image_as_Image: Image.Image
    _image_as_rotated_Image: Image.Image
    _thumb_as_Image: Image.Image
    _thumb_as_rotated_Image: Image.Image
    _video_mime: tuple[str, str] | None
    _image_mime: tuple[str, str] | None
    _thumb_mime: tuple[str, str] | None

    _temp_image_output_path: str | None

    def __init__(
            self,
            app_content: Post | Experience | Playlist,
            video: InMemoryUploadedFile | TemporaryUploadedFile,
            image: InMemoryUploadedFile | TemporaryUploadedFile,
            thumb: InMemoryUploadedFile | TemporaryUploadedFile,
        ):
        self.app_content = app_content
        self._opened_video = None
        self._opened_image = None
        self._opened_thumb = None

        self._video_mime = None
        self._image_mime = None
        self._thumb_mime = None

        self._video_info = None

        self._image_as_Image = None
        self._image_as_rotated_Image = None
        self._thumb_as_Image = None
        self._thumb_as_rotated_Image = None

        self._temp_image_output_path = None


        if video is not None:
            self._video_mime = file_handling.get_mime_type(video)
            video_url = file_handling.split_file_url(video.name)
            video_extension = video_url['extension'] or self._video_mime[1]
            video_extension = video_extension.lower()
            video.name = f'{uuid4()}.{video_extension}'
            self._opened_video = video.open('rb')
        if image is not None:
            self._image_mime = file_handling.get_mime_type(image)
            image_url = file_handling.split_file_url(image.name)
            image_extension = image_url['extension'] or self._image_mime[1]
            image_extension = image_extension.lower()
            image.name = f'{uuid4()}.{image_extension}'
            self._opened_image = image.open('rb')
        if thumb is not None:
            self._thumb_mime = file_handling.get_mime_type(thumb)
            thumb_url = file_handling.split_file_url(thumb.name)
            thumb_extension = thumb_url['extension'] or self._thumb_mime[1]
            thumb_extension = thumb_extension.lower()
            thumb.name = f'{uuid4()}.{thumb_extension}'
            self._opened_thumb = thumb.open('rb')


    def dispose(self):
        if self._opened_video is not None:
            self._opened_video.close()
        if self._opened_image is not None:
            self._opened_image.close()
        if self._opened_thumb is not None:
            self._opened_thumb.close()
        if self._temp_image_output_path is not None:
            if os.path.exists(self._temp_image_output_path):
                os.remove(self._temp_image_output_path)


    def validate_and_prep_simple_info(self):
        # Prep
        if self._opened_video is not None:
            self._video_info = file_handling.VideoInfo(self._opened_video)
        if self._opened_image is not None:
            if self._image_mime[1] in ('heic', 'heif'):
                temp_dir = PosixPath('/tmp')
                if not temp_dir.exists():
                    raise Exception('/tmp directory could not be found')
                temp_input_path: PosixPath = f'{temp_dir}/{uuid4()}.heic'
                self._temp_image_output_path = f'{temp_dir}/{uuid4()}.jpg'
                heic_bytes: bytes = None
                heic_bytes = self._opened_image.read()
                with open(temp_input_path, 'wb') as temp_file:
                    temp_file.write(heic_bytes)
                wand_image = WandImage.Image(filename=temp_input_path)
                wand_image.format = 'jpg'
                wand_image.save(filename=self._temp_image_output_path)
                os.remove(temp_input_path)
                self._image_as_Image = Image.open(self._temp_image_output_path)
                self._opened_image.name = f'{uuid4()}.jpg'
            else:
                self._image_as_Image = Image.open(self._opened_image)
            self._image_as_rotated_Image = ImageOps.exif_transpose(self._image_as_Image)
        if self._opened_thumb is not None:
            self._thumb_as_Image = Image.open(self._opened_thumb)
            self._thumb_as_rotated_Image = ImageOps.exif_transpose(self._thumb_as_Image)

        # Validation
        if self._opened_video is not None:
            self._validate_video_duration()
            self._validate_video_aspect_ratio()
            file_handling.validate_mime_type(self._opened_video,
                header_maintype=self._video_mime[0],
                header_subtype=self._video_mime[1],
                enforced_maintype='video')
            # TODO:
            # Remove this validation, web will require the server
            # to do the compression.
            self._validate_video_was_compressed()
        if self._opened_image is not None:
            file_handling.validate_mime_type(self._opened_image,
                header_maintype=self._image_mime[0],
                header_subtype=self._image_mime[1],
                enforced_maintype='image')
            self._validate_image_aspect_ratio()
        if self._opened_thumb is not None:
            file_handling.validate_mime_type(self._opened_thumb,
                header_maintype=self._thumb_mime[0],
                header_subtype=self._thumb_mime[1],
                enforced_maintype='image')
            self._validate_image_thumb_aspect_ratio()


    def compress_or_save_where_needed(self):
        if self._opened_video is None and \
            self._opened_image is None and \
            self._opened_thumb is None:
            return

        compress_provided_video = self._opened_video is not None \
                and self._provided_video_exceeds_size_thresholds()
        compress_provided_image = self._opened_image is not None \
                and self._provided_image_exceeds_size_thresholds()

        save_provided_video = self._opened_video is not None \
                and not compress_provided_video
        save_provided_image = self._opened_image is not None \
                and not compress_provided_image
        save_provided_thumb = self._opened_thumb is not None \
                and not self._provided_thumb_exceeds_size_thresholds()

        # Handle the golden path, everything is already done.
        # Likely the mobile app generated everything correctly.
        # TODO:
        # When the compressor machine is available just do this no matter what
        # but mark what needs compressing / generating in the database.
        if save_provided_video and save_provided_image and save_provided_thumb:
            self.app_content.video = self._opened_video
            self.app_content.highlight_image = self._opened_image
            self.app_content.highlight_image_thumbnail = self._opened_thumb
            return

        generate_image_from_video = not self._opened_image and self._opened_video is not None

        if save_provided_video:
            self.app_content.video = self._opened_video
        elif compress_provided_video:
            # Not handling this yet
            # For now, no video compression is happening on the server.
            raise Exception('Not implemented')
            # self._compress_video()

        if save_provided_image:
            self.app_content.highlight_image = self._opened_image
        elif compress_provided_image:
            self._compress_image()
        elif generate_image_from_video:
            self._generate_image_from_video()

        if save_provided_thumb:
            self.app_content.highlight_image_thumbnail = self._opened_thumb
        elif self._opened_image is not None:
            # This covers generating thumbnail from video
            # because the if the image is not provided
            # an image gets generated from the video
            # before this step, so an image from video
            # already exists.
            self._generate_thumbnail_from_image()


    def _validate_video_duration(self):
        # prep_video_info() sets _video_info
        assert(self._opened_video is not None)
        assert(self._video_info is not None)
        if self._video_info.duration > settings.FILE_UPLOADS['MAX_VIDEO_DURATION_SECONDS']:
            raise ValidationError(
                f"Video's duration of {self._video_info.duration} exceeds"
                " maximum duration allowed.")


    def _validate_aspect_ratio(self, width: int, height: int, err_label: str):
        aspect_ratio = width / height
        passed = False
        for allowed in settings.FILE_UPLOADS['ALLOWED_CONTENT_ASPECT_RATIOS']:
            if (abs(allowed - aspect_ratio) > 0.01):
                passed = True
        if not passed:
            msg = f"{err_label}'s dimension of {width}x{height} " \
                "is not a supported aspect ratio. " \
                "Either provide a video of a supported aspect ratio or " \
                "consider using an attachment instead"
            raise ValidationError(msg)


    def _validate_video_aspect_ratio(self):
        # prep_video_info() sets _video_info
        assert(self._opened_video is not None)
        assert(self._video_info is not None)
        width = self._video_info.width
        height = self._video_info.height
        self._validate_aspect_ratio(
            width,
            height,
            err_label='Video')


    def _validate_video_was_compressed(self):
        assert(self._opened_video is not None)
        assert(self._video_info is not None)
        MAX_DIMENSION = settings.FILE_UPLOADS['VIDEO_DIMENSION']
        MAX_SIZE_BYTES = settings.FILE_UPLOADS['MAX_VIDEO_SIZE_BYTES']
        width = self._video_info.width
        height = self._video_info.height
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            raise ValidationError(
                f"Video's dimension of {width}x{height} exceeds "
                " maximum dimension allowed.")
        if self._opened_video.size > MAX_SIZE_BYTES:
            raise ValidationError(
                f"Upload's size of {self._opened_video.size} bytes exceeds"
                " maximum size allowed for uploads of its type.")


    def _validate_image_aspect_ratio(self):
        assert(self._image_as_rotated_Image is not None)
        img = self._image_as_rotated_Image
        self._validate_aspect_ratio(
            img.width,
            img.height,
            err_label='Highlight Image')


    def _validate_image_thumb_aspect_ratio(self):
        assert(self._thumb_as_rotated_Image is not None)
        img = self._thumb_as_rotated_Image
        self._validate_aspect_ratio(
            img.width,
            img.height,
            err_label='Highlight Image Thumbnail')


    def _provided_video_exceeds_size_thresholds(self):
        assert(self._opened_video is not None)
        assert(self._video_info is not None)
        width = self._video_info.width
        height = self._video_info.height
        MAX_DIMENSION = settings.FILE_UPLOADS['VIDEO_DIMENSION']
        MAX_SIZE = settings.FILE_UPLOADS['MAX_VIDEO_SIZE_BYTES']
        width_too_big = width > MAX_DIMENSION
        height_too_big = height > MAX_DIMENSION
        bytes_too_big = self._opened_video.size > MAX_SIZE
        # TODO: Check bit rate, something like this
        # if self._video_info.bit_rate > 100000:
        #     return True
        return width_too_big or height_too_big or bytes_too_big


    def _provided_image_exceeds_size_thresholds(self):
        assert(self._opened_image is not None)
        MAX_DIMENSION = settings.FILE_UPLOADS['IMAGE_DIMENSION']
        MAX_SIZE = settings.FILE_UPLOADS['MAX_IMAGE_SIZE_BYTES']
        width = self._image_as_Image.width
        height = self._image_as_Image.height
        width_too_big = width > MAX_DIMENSION
        height_too_big = height > MAX_DIMENSION
        bytes_too_big = self._opened_image.size > MAX_SIZE
        return width_too_big or height_too_big or bytes_too_big


    def _provided_thumb_exceeds_size_thresholds(self):
        assert(self._opened_thumb is not None)
        MAX_DIMENSION = settings.FILE_UPLOADS['IMAGE_DIMENSION']
        MAX_SIZE = settings.FILE_UPLOADS['MAX_IMAGE_SIZE_BYTES']
        width = self._thumb_as_Image.width
        height = self._thumb_as_Image.height
        width_too_big = width > MAX_DIMENSION
        height_too_big = height > MAX_DIMENSION
        bytes_too_big = self._opened_image.size > MAX_SIZE
        return width_too_big or height_too_big or bytes_too_big


    def _compress_video(self, instance, video):
        video_type = self._video_info.video_type
        # TODO:
        # Detect and do the compression. Leaving this not done
        # to not add functionality to this refactor code branch.
        if video_type is InMemoryUploadedFile:
            pass
        elif video_type is TemporaryUploadedFile:
            pass
        raise Exception('Not implemented')


    def _compress_image(self):
        MAX_DIMENSION = settings.FILE_UPLOADS['IMAGE_DIMENSION']
        max_sizes = (MAX_DIMENSION, MAX_DIMENSION)
        image = self._image_as_rotated_Image.copy()
        image.thumbnail(max_sizes)
        format = self._image_as_Image.format
        blob = BytesIO()
        image.save(blob, format, optimize=True)
        file_from_blob = File(blob)
        self.app_content.highlight_image.save(
            self._opened_image.name,
            file_from_blob,
            save=False)


    def _generate_image_from_video(self):
        assert(self._opened_video is not None)
        assert(self._video_info is not None)
        # See the commented out example code below, it's not correct
        # but something similar to that is needed.


    def _generate_thumbnail_from_image(self):
        assert(self._image_as_rotated_Image is not None)
        MAX_DIMENSION = settings.FILE_UPLOADS['HIGHLIGHT_IMAGE_THUMBNAIL_MAX_DIMENSION']
        max_sizes = (MAX_DIMENSION, MAX_DIMENSION)
        image = self._image_as_rotated_Image.copy()
        image.thumbnail(max_sizes)
        format = self._image_as_Image.format
        blob = BytesIO()
        image.save(blob, format, optimize=True)
        file_from_blob = File(blob)
        self.app_content.highlight_image_thumbnail.save(
            f'{uuid4()}_compressed.jpeg',
            file_from_blob,
            save=False)

    def _generate_thumbnail_from_video(self):
        # TODO
        pass


    # def generate_highlight_image_and_thumbnail_from_video(self):
    #     if not type(self.video.file) is TemporaryUploadedFile:
    #         raise TypeError('self.video.file must be a TemporaryUploadedFile')
    #     if video_info is None:
    #         video_info = file_handling.get_video_info(input_path)
    #     input_path = self.video.file.temporary_file_path()
    #     temp_dir = PosixPath('/tmp')
    #     if not temp_dir.exists():
    #         raise Exception('/tmp directory could not be found')
    #     file_type = 'JPEG'
    #     screenshot_path: PosixPath = temp_dir / f'{uuid4()}.{file_type}'
    #     file_handling.take_screenshot(
    #         input_path,
    #         seconds=video_info['duration'] / 3,
    #         output_path=screenshot_path,
    #     )
    #     with Image.open(screenshot_path) as highlight_image:
    #         blob = BytesIO()
    #         highlight_image.save(blob, file_type, optimize=True)
    #         file_from_blob = File(blob)
    #         self.highlight_image.save(
    #             f'{uuid4()}.{file_type}',
    #             file_from_blob,
    #             save=save
    #         )
    #         max_allowed_dimension = settings.FILE_UPLOADS['HIGHLIGHT_IMAGE_THUMBNAIL_MAX_DIMENSION']
    #         thumbnail = highlight_image.copy()
    #         thumbnail.thumbnail((max_allowed_dimension, max_allowed_dimension))
    #         blob = BytesIO()
    #         thumbnail.save(blob, file_type, optimize=True, quality=60)
    #         thumb_from_blob = File(blob)
    #         self.highlight_image_thumbnail.save(
    #             f'{uuid4()}.{file_type}',
    #             thumb_from_blob,
    #             save=save
    #         )
    #     screenshot_path.unlink()
