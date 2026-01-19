import io
import uuid
from PIL import Image
from django.conf import settings
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.db.models import (
    CharField,
    BooleanField,
    DateTimeField,
    ImageField,
    ManyToManyField,
    PositiveSmallIntegerField,
)
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import CICharField
from django.core.files.base import File

from api.enums import (
    Publicity,
    UserType,
)
from api.models import (
    SavePersonalBucketList,
    ExperienceCompletion,
    PlaylistCompletion,
    PlaylistAccept,
    PlaylistSave,
    ExperienceAccept,
    ExperienceSave,
    PlaylistPin,
)
from api.validators import UsernameCharacterValidator


class LowercaseEmailField(CharField):
    '''calls lower() before saving to the database'''
    def to_python(self, value):
        value = super().to_python(value)
        if isinstance(value, str):
            return value.lower()
        return value

class User(AbstractUser):
    created_at = DateTimeField(auto_now_add=True)
    username = CICharField(
        max_length=150,
        unique= True,
        help_text="Required. 150 characters or fewer. Letters, digits and ./+/-/_ only.",
        validators=[
            UsernameCharacterValidator(),
        ],
        error_messages={"unique": "A user with that username already exists."},
        verbose_name="username",)
    phone = CharField(max_length=30, blank=True, null=True)
    email = LowercaseEmailField(
        max_length=254,
        unique=True,
        verbose_name='email address')
    email_verified = BooleanField(default=False, verbose_name='email verified')
    verification_code = CharField(blank=True, null=True, max_length=8, verbose_name='verification code')
    code_requested_at = DateTimeField(blank=True, null=True)
    user_type = PositiveSmallIntegerField(choices=UserType.choices, default = UserType.UNVERIFIED)
    profile_picture = ImageField(blank=True, null=True, max_length=1000, upload_to='profile_pictures')
    profile_picture_thumbnail = ImageField(blank=True, null=True, max_length=1000, upload_to='profile_pictures')
    life_frame_id = CharField(blank=True, null=True, max_length=50, verbose_name='LifeFrame ID')
    apple_user_id = CharField(max_length=50, blank=True, null=True, verbose_name='Apple User ID')
    google_user_id = CharField(max_length=50, blank=True, null=True, verbose_name='Google User ID')
    facebook_user_id = CharField(max_length=50, blank=True, null=True, verbose_name='Facebook User ID')
    notify_about_new_content_reports = BooleanField(default=False,
        help_text='Will be emailed about new Reports that are created in the mobile app. ' + \
            'This should be a user who has the ability to resolve Reports, like a member of the Admin group. ' + \
            'Will not be emailed if not "Email verified" and not "Staff status"')
    follows = ManyToManyField("self", through='UserFollow')
    blocks = ManyToManyField('self', through='UserBlock')
    seen_experiences = ManyToManyField('Experience', blank=True)
    seen_playlists = ManyToManyField('Playlist', blank=True)
    seen_posts = ManyToManyField('Post')
    accepted_experiences = ManyToManyField('Experience', blank=True, through=ExperienceAccept, related_name='users_accepted',)
    accepted_playlists = ManyToManyField('Playlist', blank=True, through=PlaylistAccept, related_name='users_accepted')
    completed_experiences = ManyToManyField('Experience', blank=True, through=ExperienceCompletion, related_name='users_completed')
    completed_playlists = ManyToManyField('Playlist', blank=True, through=PlaylistCompletion, related_name='users_completed')
    saved_experiences = ManyToManyField('Experience', blank=True, through=ExperienceSave, related_name='users_saved')
    bucket_list = ManyToManyField('Experience', blank=True, through=SavePersonalBucketList, related_name='users_bucket_list')
    saved_playlists = ManyToManyField('Playlist', blank=True, through=PlaylistSave, related_name='users_saved')
    pinned_playlists = ManyToManyField('Playlist', blank=True, through=PlaylistPin, related_name='users_pinned')
    name = CharField(blank=True, null=True, max_length=50)
    tagline = CharField(blank=True, null=True, max_length=200)
    bio = CharField(blank=True, null=True, max_length=5000)
    website = CharField(blank=True, null=True, max_length=2048)
    birthdate = DateTimeField(blank=True, null=True)
    experience_visibility = PositiveSmallIntegerField(choices=Publicity.choices, default=Publicity.PUBLIC)
    badge_visibility = PositiveSmallIntegerField(choices=Publicity.choices, default=Publicity.PUBLIC)
    activity_push_pref = BooleanField(
        default=True,
        verbose_name='General notification preference',
        help_text="Overall notification preference. If this is false, no non-message notifications will be triggered",)
    like_push_pref = BooleanField(default=True, verbose_name='Like notification preference')
    mention_push_pref = BooleanField(default=True, verbose_name='Mention notification preference')
    comment_push_pref = BooleanField(default=True, verbose_name='Comment notification preference')
    follow_push_pref = BooleanField(default=True, verbose_name='New or accepted follow notification preference')
    follow_request_push_pref = BooleanField(default=True, verbose_name='New incoming follow request notification preference')
    accept_complete_push_pref = BooleanField(default=True, verbose_name='Experience and Playlist accept or complete notification preference')
    exp_of_the_day_push_pref = BooleanField(default=True, verbose_name='Experience of the day notification preference')


    def set_profile_picture(self, profile_picture: InMemoryUploadedFile | TemporaryUploadedFile):
        '''Set the profile picture and generate and set a thumbnail. Does not call save() the model.'''
        if profile_picture is None:
            raise Exception("profile_picture not found")
        full_image = Image.open(profile_picture)
        width: int = full_image.size[0]
        height: int = full_image.size[1]
        max_dimension: int = settings.FILE_UPLOADS['PROFILE_PICTURE_MAX_DIMENSION']
        if width > max_dimension or height > max_dimension:
            factor = max_dimension / min(width, height)
            size = (int(width * factor), int(height * factor))
            full_image = full_image.resize(size, Image.Resampling.LANCZOS)

        max_thumb_dimension: int = settings.FILE_UPLOADS['PROFILE_PICTURE_THUMBNAIL_MAX_DIMENSION']
        thumbnail = full_image.copy()
        thumbnail.thumbnail((max_thumb_dimension, max_thumb_dimension))
        # uuid4 avoids caching on the mobile app
        hash = uuid.uuid4()
        full_image_filename = f'{hash}.jpg'
        thumbnail_image_filename = f'{hash}-thumbnail.jpg'

        # `save=False` since the default save=True means that the parent
        # model's save method would be called after the image is saved.
        # This is to avoid recursion / infinite loop.
        blob = io.BytesIO()
        full_image.save(blob, 'JPEG', optimize=True, quality=95)
        self.profile_picture.save(full_image_filename, File(blob), save=False)
        blob = io.BytesIO()
        thumbnail.save(blob, 'JPEG', optimize=True, quality=75)
        self.profile_picture_thumbnail.save(thumbnail_image_filename, File(blob), save=False)

    @property
    def obfuscated_phone(self):
        if self.phone is None:
            return None
        obfuscator = '*'
        phone = list(self.phone)
        phone_show = phone[-3:]
        phone_obfuscate = phone[:-3]
        for i in range(len(phone_obfuscate)):
            char = phone_obfuscate[i]
            if char.isdigit():
                phone_obfuscate[i] = obfuscator
        phone_obfuscate_str = ''.join(phone_obfuscate)
        phone_show_str = ''.join(phone_show)
        return f'{phone_obfuscate_str}{phone_show_str}'

    @property
    def obfuscated_email(self):
        obfuscator = '*'
        email: str = self.email
        email_split: str = email.split('@')
        email_name = list(email_split[0])
        email_host = email_split[1]
        for i in range(len(email_name)):
            if i == 0:
                continue
            if i == len(email_name) - 1:
                continue
            email_name[i] = obfuscator
        parts = [
            "".join(email_name),
            '@',
            email_host,
        ]
        return ''.join(parts)

    # check if username is owned by another user case insensitive
    def clean(self):
        username_owner = get_user_model().objects.filter(username__iexact=self.username).first()
        if username_owner != None:
            if username_owner.id != self.id:
                raise ValidationError("Username is not unique", code='unique')
        super().clean()

    def __str__(self):
        return f'@{self.username}'
