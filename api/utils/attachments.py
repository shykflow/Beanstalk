import os
import subprocess

from io import BytesIO
from PIL import ImageOps, Image
from uuid import uuid4
from pathlib import PosixPath

from django.conf import settings
from django.core.files.base import File
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile
)
from django.core.exceptions import ValidationError
from api.enums import AttachmentType

from api.models import Attachment
from api.utils import file_handling

"""
The flutter app compresses on the client if mobile, this checks
if the file needs compressing, if already small enough, it just returns.
The admin panel does not provide compression.
"""


class AttachmentFileHandler:
    _attachment: Attachment
    _attachment_type: AttachmentType

    _file: InMemoryUploadedFile | TemporaryUploadedFile
    _thumbnail: InMemoryUploadedFile | TemporaryUploadedFile
    _file_mime: tuple[str, str]
    _thumb_mime: tuple[str, str] | None

    _video_info: file_handling.VideoInfo
    _file_as_Image: Image.Image
    _file_as_rotated_Image: Image.Image
    _file_thumbnail_as_Image: Image.Image
    _file_thumbnail_as_rotated_Image: Image.Image

    _file_bytes: bytes
    _thumbnail_bytes: bytes

    def __init__(
            self,
            attachment: Attachment,
            file: InMemoryUploadedFile | TemporaryUploadedFile,
            thumbnail: InMemoryUploadedFile | TemporaryUploadedFile | None,
        ):
        assert(attachment is not None)
        assert(file is not None)

        self._file_mime = file_handling.get_mime_type(file)
        self._thumb_mime = None
        file_url = file_handling.split_file_url(file.name)
        file_extension = file_url['extension'] or self._file_mime[1]
        file.name = f'{uuid4()}.{file_extension}'
        if thumbnail is not None:
            self._thumb_mime = file_handling.get_mime_type(thumbnail)
            thumb_url = file_handling.split_file_url(thumbnail.name)
            thumb_extension = thumb_url['extension'] or self._thumb_mime[1]
            thumbnail.name = f'{uuid4()}_thumb.{thumb_extension}'

        self._attachment = attachment
        self._attachment_type = None
        self._file = file
        self._thumbnail = thumbnail
        self._video_info = None
        self._file_as_Image = None
        self._file_as_rotated_Image = None
        self._file_thumbnail_as_Image = None
        self._file_thumbnail_as_rotated_Image = None
        self._file_bytes = None
        self._thumbnail_bytes = None


    def dispose(self):
        # Avoid circular references so the garbage collection is easier
        self._attachment = None
        self._attachment_type = None
        self._file = None
        self._thumbnail = None
        self._file_mime = None
        self._thumb_mime = None
        self._video_info = None
        self._file_as_Image = None
        self._file_as_rotated_Image = None
        self._file_thumbnail_as_Image = None
        self._file_thumbnail_as_rotated_Image = None
        self._file_bytes = None
        self._thumbnail_bytes = None

    def validate_and_prep_simple_info(self):
        MAX_SIZE_BYTES: int = settings.FILE_UPLOADS['ATTACHMENTS']['MAX_FILE_SIZE']
        MAX_VIDEO_DURATION_SECONDS: int = settings.FILE_UPLOADS['MAX_VIDEO_DURATION_SECONDS']

        file_handling.validate_mime_type(self._file,
            header_maintype=self._file_mime[0],
            header_subtype=self._file_mime[1])

        if self._thumbnail is not None:
            file_handling.validate_mime_type(self._thumbnail,
                header_maintype=self._thumb_mime[0],
                header_subtype=self._thumb_mime[1],
                enforced_maintype='image')

        self._attachment_type = AttachmentType.from_string(self._file_mime[0])

        if self._attachment_type == AttachmentType.VIDEO:
            self._video_info = file_handling.VideoInfo(self._file)
            if self._video_info.duration > MAX_VIDEO_DURATION_SECONDS:
                raise ValidationError(
                    f"Video duration of {self._video_info.duration} exceeds"
                    f" maximum seconds of {MAX_VIDEO_DURATION_SECONDS}.")
            if self._file.size > MAX_SIZE_BYTES:
                # TODO: Remove this and do compression on the server side.
                raise ValidationError(
                    f"Upload's size of {self._file.size} bytes exceeds"
                    " maximum size allowed for uploads of its type.")

        elif self._attachment_type == AttachmentType.IMAGE:
            self._file_as_Image = Image.open(self._file)
            self._file_as_rotated_Image = ImageOps.exif_transpose(
                self._file_as_Image)

        elif self._attachment_type == AttachmentType.OTHER:
            if self._file.size > MAX_SIZE_BYTES:
                raise ValidationError(
                    f"Upload's size of {self._file.size} bytes exceeds"
                    " maximum size allowed for uploads of its type.")

        if self._thumbnail is not None:
            MAX_THUMB_FILE_SIZE = settings.FILE_UPLOADS['ATTACHMENTS']['MAX_THUMB_FILE_SIZE']
            size = self._thumbnail.size
            if size > MAX_THUMB_FILE_SIZE:
                self._thumbnail = None
            else:
                self._file_thumbnail_as_Image = Image.open(self._thumbnail)
                self._file_thumbnail_as_rotated_Image = ImageOps.exif_transpose(
                    self._file_thumbnail_as_Image)


    def compress_and_set_files(self):
        if self._attachment_type == AttachmentType.VIDEO:
            assert(self._video_info is not None)
            self._attachment.file = self._file
            # TODO: compress video if needed
            # self._compress_video_and_set()    # Not implemented yet
            # self._generate_thumb_from_video() # Not implemented yet
        elif self._attachment_type == AttachmentType.IMAGE:
            assert(self._file_as_Image is not None)
            assert(self._file_as_rotated_Image is not None)
            if self._file_mime[1] == 'gif':
                self._compress_gif_and_set()
                if self._thumbnail is None:
                    self._generate_thumb_from_gif()
            else:
                self._compress_image()
                if self._thumbnail is None:
                    self._generate_thumb_from_image()
        elif self._attachment_type == AttachmentType.OTHER:
            self._attachment.file = self._file
        else:
            raise Exception()

        if self._thumbnail is not None:
            self._attachment.thumbnail = self._thumbnail


    def _compress_video_and_set(self):
        raise Exception('Not implemented')


    def _generate_thumb_from_video(self):
        raise Exception('Not implemented')

    def _get_file_bytes(self):
        if self._file_bytes is None:
            with self._file.open('rb') as file:
                file.seek(0)
                self._file_bytes: bytes = file.read()
        return self._file_bytes

    def _get_thumbnail_bytes(self):
        if self._thumbnail_bytes is None:
            with self._thumbnail.open('rb') as file:
                file.seek(0)
                self._thumbnail_bytes: bytes = file.read()
        return self._thumbnail_bytes


    def _compress_gif_and_set(self):
        MAX_DIMENSION: int = settings.FILE_UPLOADS['ATTACHMENTS']['MAX_IMAGE_COMPRESS_DIMENSION']['GIF']
        gif = self._file_as_rotated_Image
        width_small_enough = gif.width <= MAX_DIMENSION
        height_small_enough = gif.height <= MAX_DIMENSION
        if width_small_enough and height_small_enough:
            file_bytes = self._get_file_bytes()
            filename_split = self._file.name.split('.')
            ext = filename_split[len(filename_split)-1].lower()
            name = f'{uuid4()}.{ext}'
            bytes_io = BytesIO(file_bytes)
            self._attachment.file.save(name, bytes_io, save=False)
            return
        # TODO: Look into if a small-dimension gif could be too large,
        # TODO: re-compress if too big.
        temp_dir = PosixPath('/tmp')
        if not temp_dir.exists():
            raise Exception('/tmp directory could not be found')
        identifier = str(uuid4())
        input_file_name = f'{identifier}.gif'
        output_file_name = f'compressed_{identifier}.gif'
        input_path = f'{temp_dir}/{input_file_name}'
        output_path = f'{temp_dir}/{output_file_name}'
        try:
            # Write the file bytes to a temp file so FFMPEG can
            # use it to compress a new output file.
            with self._file.open() as file:
                file.seek(0)
                original_bytes = file.read()
                with open(input_path, 'wb') as temp_file:
                    temp_file.write(original_bytes)
            # Compress
            filter_complex = \
                '[0:v] ' + \
                f'fps=15,scale={MAX_DIMENSION}:-1:flags=lanczos,split [a][b]; ' + \
                '[a] ' + \
                'palettegen=reserve_transparent=on:transparency_color=ffffff:stats_mode=diff [p]; ' + \
                '[b][p] ' + \
                'paletteuse'
            command = [
                'ffmpeg',
                '-hide_banner',
                '-v', 'warning',
                '-i', input_path,
                '-filter_complex', filter_complex,
                output_path,
            ]
            process = subprocess.run(command)
            if process.returncode != 0:
                raise Exception()
            with open(output_path, 'rb') as output_file:
                self._attachment.file.save(output_file_name, output_file, save=False)
        finally:
            # Cleanup
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)


    def _generate_thumb_from_gif(self):
        temp_dir = PosixPath('/tmp')
        if not temp_dir.exists():
            raise Exception('/tmp directory could not be found')
        identifier = str(uuid4())
        input_file_name = f'{identifier}.gif'
        output_file_name = f'{identifier}_thumb.jpg'
        input_path = f'{temp_dir}/{input_file_name}'
        output_path = f'{temp_dir}/{output_file_name}'
        try:
            file_bytes = self._get_file_bytes()
            with open(input_path, 'wb') as temp_input_file:
                temp_input_file.write(file_bytes)
            # Compress
            command = [
                'ffmpeg',
                '-hide_banner',
                '-v', 'warning',
                '-i', input_path,
                '-frames:v', '1',
                output_path,
            ]
            process = subprocess.run(command)
            if process.returncode != 0:
                raise Exception()
            output_file = Image.open(output_path)
            blob = BytesIO()
            output_file.save(blob, format='JPEG', optimize=True, quality=60)
            output_file.close()
            self._attachment.thumbnail.save(output_file_name, File(blob), save=False)
        finally:
            # Cleanup
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)


    def _compress_image(self):
        assert(self._file_as_Image is not None)
        assert(self._file_as_rotated_Image is not None)
        _format = self._file_as_Image.format
        image = self._file_as_rotated_Image
        MAX_SIZE_BYTES = settings.FILE_UPLOADS['ATTACHMENTS']['MAX_FILE_SIZE']

        small_enough_in_bytes = self._file.size <= MAX_SIZE_BYTES
        if small_enough_in_bytes:
            blob = BytesIO()
            image.save(blob, _format, optimize=True, quality=60)
            self._attachment.file.save(f'{uuid4()}.{_format}', File(blob), save=False)
            return

        MAX_DIMENSION = settings.FILE_UPLOADS['ATTACHMENTS']['MAX_IMAGE_COMPRESS_DIMENSION']['IMAGE']
        image = self._file_as_rotated_Image
        max_dimensions = (min(image.width, MAX_DIMENSION), min(image.height, MAX_DIMENSION))
        image.thumbnail(max_dimensions)
        blob = BytesIO()
        image.save(blob, _format, optimize=True, quality=60)
        self._attachment.file.save(f'{uuid4()}.{_format}', File(blob), save=False)


    def _generate_thumb_from_image(self):
        # The flutter app could have provided a compressed thumbnail
        if self._thumbnail is not None:
            MAX_THUMB_FILE_SIZE = settings.FILE_UPLOADS['ATTACHMENTS']['MAX_THUMB_FILE_SIZE']
            size = self._thumbnail.size
            if size <= MAX_THUMB_FILE_SIZE:
                return
        MAX_DIMENSION = settings.FILE_UPLOADS['ATTACHMENTS']['THUMBNAIL_COMPRESS_TO_DIMENSION']['IMAGE']
        # the transpose loses the format value, it becomes None
        image = self._file_as_rotated_Image
        max_dimensions = (MAX_DIMENSION, MAX_DIMENSION)
        image.thumbnail(max_dimensions)
        blob = BytesIO()
        image.save(blob, 'JPEG', optimize=True, quality=30)
        self._attachment.thumbnail.save(f'{uuid4()}_thumb.jpg', File(blob), save=False)
