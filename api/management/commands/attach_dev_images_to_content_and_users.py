from os import walk
import uuid
import logging
import random
from django.db import connection
from django.conf import settings
from django.core.files.base import File
from django.core.management.base import BaseCommand

from api.models import (
    CategoryMapping,
    Experience,
    Playlist,
    Post,
    User,
)
from api.utils.command_line_spinner import CommandLineSpinner
from api.utils.file_handling import split_file_url

logger = logging.getLogger('app')


class Command(BaseCommand):
    bypass_spinners = False
    assets_dir = f'{settings.BASE_DIR}/api/management/commands/assets'

    # These will be auto-detected from files in the assets_dir
    category_mapping_filenames = []
    hightlight_images = []
    profile_pictures = []

    # mappings of filename => uuid for reusing the same file upload
    filename_uuids: dict[str, str] = {}

    def handle(self, *args, **options):
        logger.info(
            'Running python manage.py attach_dev_images_to_content_and_users')
        self.set_filenames()
        self.set_category_mapping_images()
        self.set_playlist_images()
        self.set_experience_images()
        self.set_post_images()
        self.set_user_images()

    def set_filenames(self):
        print('Gathering files to upload')
        _dir = f'{Command.assets_dir}/category_mapping_images'
        for (dirpath, dirnames, filenames) in walk(_dir):
            for filename in filenames:
                Command.category_mapping_filenames.append(filename)
        _dir = f'{Command.assets_dir}/highlight_images'
        for (dirpath, dirnames, filenames) in walk(_dir):
            for filename in filenames:
                Command.hightlight_images.append(filename)
        _dir = f'{Command.assets_dir}/profile_pictures'
        for (dirpath, dirnames, filenames) in walk(_dir):
            for filename in filenames:
                Command.profile_pictures.append(filename)

    def set_category_mapping_images(self):
        with CommandLineSpinner(
            'Setting some Category Mapping images',
            bypass_spinning=Command.bypass_spinners):
            bucket_upload_to = CategoryMapping.image.field.upload_to
            for item in CategoryMapping.objects.all():
                if bool(item.image):
                    continue
                if random.randint(0, 2) == 0:
                    continue
                filename = random.choice(Command.category_mapping_filenames)
                split = split_file_url(filename)
                _uuid = Command.filename_uuids.get(filename)
                already_uploaded = False
                if _uuid is None:
                    _uuid = uuid.uuid4()
                    Command.filename_uuids[filename] = _uuid
                else:
                    already_uploaded = True
                upload_name = f"{_uuid}.{split['extension']}"
                if already_uploaded:
                    with connection.cursor() as cursor:
                        sql = f"""
                            UPDATE api_categorymapping
                            SET image = %(image)s
                            WHERE id = %(id)s
                        """
                        params = {
                            'id': item.id,
                            'image': f'{bucket_upload_to}/{upload_name}'
                        }
                        cursor.execute(sql, params)
                else:
                    full_file_path = f'{Command.assets_dir}/category_mapping_images/{filename}'
                    with open(full_file_path, 'rb') as file:
                        item.image.save(upload_name, File(file))


    def set_playlist_images(self):
        with CommandLineSpinner(
            'Setting some Playlist images',
            bypass_spinning=Command.bypass_spinners):
            bucket_upload_to = Playlist.highlight_image.field.upload_to
            for playlist in Playlist.objects.all():
                if bool(playlist.highlight_image):
                    continue
                if random.randint(0, 2) == 0:
                    continue
                filename = random.choice(Command.hightlight_images)
                split = split_file_url(filename)
                _uuid = Command.filename_uuids.get(filename)
                already_uploaded = False
                if _uuid is None:
                    _uuid = uuid.uuid4()
                    Command.filename_uuids[filename] = _uuid
                else:
                    already_uploaded = True
                upload_name = f"{_uuid}.{split['extension']}"
                if already_uploaded:
                    with connection.cursor() as cursor:
                        sql = f"""
                            UPDATE api_playlist
                            SET
                                highlight_image = %(image)s,
                                highlight_image_thumbnail = %(image)s
                            WHERE id = %(id)s
                        """
                        params = {
                            'id': playlist.id,
                            'image': f'{bucket_upload_to}/{upload_name}',
                        }
                        cursor.execute(sql, params)
                else:
                    full_file_path = f'{Command.assets_dir}/highlight_images/{filename}'
                    with open(full_file_path, 'rb') as file:
                        playlist.highlight_image.save(upload_name, File(file))
                    with connection.cursor() as cursor:
                        sql = f"""
                            UPDATE api_playlist
                            SET
                                highlight_image_thumbnail = %(image)s
                            WHERE id = %(id)s
                        """
                        params = {
                            'id': playlist.id,
                            'image': f'{bucket_upload_to}/{upload_name}',
                        }
                        cursor.execute(sql, params)


    def set_experience_images(self):
        with CommandLineSpinner(
            'Setting some Experience images',
            bypass_spinning=Command.bypass_spinners):
            bucket_upload_to = Experience.highlight_image.field.upload_to
            for item in Experience.objects.all():
                if bool(item.highlight_image):
                    continue
                if random.randint(0, 2) == 0:
                    continue
                filename = random.choice(Command.hightlight_images)
                split = split_file_url(filename)
                _uuid = Command.filename_uuids.get(filename)
                already_uploaded = False
                if _uuid is None:
                    _uuid = uuid.uuid4()
                    Command.filename_uuids[filename] = _uuid
                else:
                    already_uploaded = True
                upload_name = f"{_uuid}.{split['extension']}"
                if already_uploaded:
                    with connection.cursor() as cursor:
                        sql = f"""
                            UPDATE api_experience
                            SET
                                highlight_image = %(image)s,
                                highlight_image_thumbnail = %(image)s
                            WHERE id = %(id)s
                        """
                        params = {
                            'id': item.id,
                            'image': f'{bucket_upload_to}/{upload_name}',
                        }
                        cursor.execute(sql, params)
                else:
                    full_file_path = f'{Command.assets_dir}/highlight_images/{filename}'
                    with open(full_file_path, 'rb') as file:
                        item.highlight_image.save(upload_name, File(file))
                    with connection.cursor() as cursor:
                        sql = f"""
                            UPDATE api_experience
                            SET
                                highlight_image_thumbnail = %(image)s
                            WHERE id = %(id)s
                        """
                        params = {
                            'id': item.id,
                            'image': f'{bucket_upload_to}/{upload_name}',
                        }
                        cursor.execute(sql, params)


    def set_post_images(self):
        with CommandLineSpinner(
            'Setting some Post images',
            bypass_spinning=Command.bypass_spinners):
            bucket_upload_to = Experience.highlight_image.field.upload_to
            for item in Post.objects.all():
                if bool(item.highlight_image):
                    continue
                if random.randint(0, 2) == 0:
                    continue
                filename = random.choice(Command.hightlight_images)
                split = split_file_url(filename)
                _uuid = Command.filename_uuids.get(filename)
                already_uploaded = False
                if _uuid is None:
                    _uuid = uuid.uuid4()
                    Command.filename_uuids[filename] = _uuid
                else:
                    already_uploaded = True
                upload_name = f"{_uuid}.{split['extension']}"
                if already_uploaded:
                    with connection.cursor() as cursor:
                        sql = f"""
                            UPDATE api_post
                            SET
                                highlight_image = %(image)s,
                                highlight_image_thumbnail = %(image)s
                            WHERE id = %(id)s
                        """
                        params = {
                            'id': item.id,
                            'image': f'{bucket_upload_to}/{upload_name}',
                        }
                        cursor.execute(sql, params)
                else:
                    full_file_path = f'{Command.assets_dir}/highlight_images/{filename}'
                    with open(full_file_path, 'rb') as file:
                        item.highlight_image.save(upload_name, File(file))
                    with connection.cursor() as cursor:
                        sql = f"""
                            UPDATE api_post
                            SET
                                highlight_image_thumbnail = %(image)s
                            WHERE id = %(id)s
                        """
                        params = {
                            'id': item.id,
                            'image': f'{bucket_upload_to}/{upload_name}',
                        }
                        cursor.execute(sql, params)

    def set_user_images(self):
        with CommandLineSpinner(
            'Setting some User images',
            bypass_spinning=Command.bypass_spinners):
            bucket_upload_to = User.profile_picture.field.upload_to
            for user in User.objects.all():
                if bool(user.profile_picture):
                    continue
                # Seed script adds one inactive user so we'll always set
                # a profile picture for that user. This is to ensure that
                # we hide their profile picture in the app.
                if user.is_active and random.randint(0, 2) == 0:
                    continue
                filename = random.choice(Command.profile_pictures)
                split = split_file_url(filename)
                _uuid = Command.filename_uuids.get(filename)
                already_uploaded = False
                if _uuid is None:
                    _uuid = uuid.uuid4()
                    Command.filename_uuids[filename] = _uuid
                else:
                    already_uploaded = True
                upload_name = f"{_uuid}.{split['extension']}"
                if already_uploaded:
                    with connection.cursor() as cursor:
                        sql = f"""
                            UPDATE api_user
                            SET
                                profile_picture = %(image)s,
                                profile_picture_thumbnail = %(image)s
                            WHERE id = %(id)s
                        """
                        params = {
                            'id': user.id,
                            'image': f'{bucket_upload_to}/{upload_name}',
                        }
                        cursor.execute(sql, params)
                else:
                    full_file_path = f'{Command.assets_dir}/profile_pictures/{filename}'
                    with open(full_file_path, 'rb') as file:
                        user.profile_picture.save(upload_name, File(file))
                    with connection.cursor() as cursor:
                        sql = f"""
                            UPDATE api_user
                            SET
                                profile_picture_thumbnail = %(image)s
                            WHERE id = %(id)s
                        """
                        params = {
                            'id': user.id,
                            'image': f'{bucket_upload_to}/{upload_name}',
                        }
                        cursor.execute(sql, params)
