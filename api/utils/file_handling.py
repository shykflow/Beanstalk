import json
import os
import subprocess

import magic
import subprocess

from pathlib import PosixPath

from django.conf import settings
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile,
)
from django.core.exceptions import SuspiciousFileOperation, ValidationError


class VideoInfo:
    def __init__(self, video: InMemoryUploadedFile | TemporaryUploadedFile) -> None:
        if video.closed:
                raise ValidationError('Video is unreadable')
        self.video_type = type(video)
        command = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'format=duration:stream=width,height',
            '-show_format',
            '-of', 'json',
            '-loglevel', settings.FFPROBE_LOG_LEVEL,
        ]
        kwargs = {}
        if self.video_type is InMemoryUploadedFile:
            video.seek(0)
            _bytes: bytes = video.read()
            command.append('-')
            kwargs['input'] = _bytes
        elif self.video_type is TemporaryUploadedFile:
            temp_path = video.temporary_file_path()
            command.append(temp_path)
        result = subprocess.check_output(command, **kwargs)
        json_dict = json.loads(result)
        self.duration = float(json_dict['format']['duration'])
        self.width = json_dict['streams'][0]['width']
        self.height = json_dict['streams'][0]['height']
        self.format_name = json_dict['format']['format_name']

        bit_rate = json_dict['format'].get('bit_rate')
        if bit_rate is None:
            self.bit_rate = int((video.size * 8) / self.duration)
        else:
            self.bit_rate = int(bit_rate)


def split_file_url(url: str) -> dict[str, str]:
    """
    Return the URL of a file as a dictionary in the following format:
    ```
    {
        'path':      str (the directory path leading to the file,    or '' if none was found),
        'name':      str (the name of the file without the extension or '' if none was found),
        'extension': str (the file extension, not including the '.'  or '' if none was found),
    }
    ```
    """
    if url is None:
        return {
            'path': '',
            'name': '',
            'extension': '',
        }
    dir_path = ''
    name = ''
    extension = ''
    path_split = os.path.split(url)
    dir_path = path_split[0]
    file_name = ''
    if len(path_split) > 1:
        file_name = path_split[1]

    if dir_path != '' and not dir_path.endswith('/'):
        dir_path = dir_path + '/'
    if file_name:
        last_dot_index = file_name.rfind('.')
        if last_dot_index in (-1, 0):
            name = file_name
        else:
            name = file_name[:last_dot_index]
            extension = file_name[last_dot_index+1:]
    return {
        'path': dir_path,
        'name': name,
        'extension': extension,
    }


def get_mime_type(
    file: InMemoryUploadedFile | TemporaryUploadedFile) -> tuple[str, str]:
    claimed_mime_type = file.content_type.lower()
    maintype, subtype = claimed_mime_type.split('/')
    return maintype, subtype


def validate_mime_type(
    file: InMemoryUploadedFile | TemporaryUploadedFile,
    header_maintype: str, header_subtype: str,
    enforced_maintype: str | None = None):
    # Validate that this file format is allowed and expected
    ALLOWED_MIME_TYPES = settings.ALLOWED_MIME_TYPES
    MIME_TYPE_EQUIVALENTS = settings.MIME_TYPE_EQUIVALENTS
    allowed_subtypes = ALLOWED_MIME_TYPES.get(header_maintype)
    error_message = None
    if enforced_maintype is not None and header_maintype != enforced_maintype:
        error_message = (
            f"'{enforced_maintype}' MIME type was expected, but"
            f" '{header_maintype}' MIME type was read."
        )
    elif header_maintype not in ALLOWED_MIME_TYPES:
        error_message = f"'{header_maintype}' MIME types are not supported."
    elif header_subtype not in allowed_subtypes:
        error_message = (
            f"'{header_subtype}' MIME type not supported, supported {header_maintype} "
            f"MIME types are {', '.join(allowed_subtypes)}."
        )
    if error_message is not None:
        raise ValidationError(error_message)
    read_binary: bytes
    # Validate that this file format is what it is claiming to be
    file.seek(0)
    read_binary = file.read(settings.MAGIC_CHUNK_SIZE)
    read_mime_type = magic.from_buffer(read_binary, mime=True).lower()
    full_header_type = f'{header_maintype}/{header_subtype}'

    exception = SuspiciousFileOperation(
        f"{file.name}'s file extension implies '{full_header_type}'"
        f" MIME type, but '{read_mime_type}' MIME type was read.")

    if read_mime_type in MIME_TYPE_EQUIVALENTS['jpeg']:
        if full_header_type not in MIME_TYPE_EQUIVALENTS['jpeg']:
            raise exception
    elif read_mime_type in MIME_TYPE_EQUIVALENTS['msword']:
        if full_header_type not in MIME_TYPE_EQUIVALENTS['msword']:
            raise exception
    elif read_mime_type != full_header_type:
        raise exception


def take_screenshot(
    input_path: str, seconds: float, output_path: PosixPath,
    scale: str | None = None) -> bool:
    """
    Creates an image from 1 frame of a video using ffmpeg.

    `input_path` is the URL of the video that the screenshot will be taken from

    `seconds` is how far into the video the screenshot will be taken

    `output_path` is the full path to where the output file will be created, including
    the name of the file and its file extension.

    `scale` is an optional parameter to specify the scale of the output image,
    in `300x200` format, where `300` is the width and `200` is the height.
    """
    if output_path.exists():
        raise FileExistsError(f'{(output_path.resolve())} already exists')
    command = [
        'ffmpeg',
        '-v', 'error',
        '-ss', str(seconds),
        '-i', input_path,
        '-frames:v', '1',
    ]
    if scale is not None:
        command += ['-s', scale]
    command.append(str(output_path.resolve()))
    result = subprocess.run(command)
    if result.returncode != 0 or not output_path.exists():
        raise FileNotFoundError('Could not take screenshot')
