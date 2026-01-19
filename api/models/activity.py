from django.forms import ValidationError
from django.utils import timezone
from django.db.models.deletion import CASCADE, SET_NULL
from django.db import models

from api.enums import ActivityType
from api.utils.activity import ActivityUtils

class Activity(models.Model):
    class Meta:
        verbose_name_plural = 'Activities'

    user = models.ForeignKey('User', on_delete=CASCADE)
    type = models.PositiveSmallIntegerField(choices=ActivityType.choices)
    seen = models.BooleanField(default=False,)
    is_push = models.BooleanField(default=False,)
    has_pushed = models.BooleanField(default=False)
    aggregated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_time = models.DateTimeField(blank=True, null=True)
    related_user = models.ForeignKey('User', on_delete=SET_NULL, blank=True, null=True, related_name='related_user')
    post = models.ForeignKey('Post', on_delete=CASCADE, blank=True, null=True)
    comment = models.ForeignKey('Comment', on_delete=CASCADE, blank=True, null=True,
        help_text='The comment that related_user commented on. It is the parent of related_comment.')
    related_comment = models.ForeignKey('Comment', on_delete=CASCADE, blank=True, null=True, related_name='related_comment',
        help_text='The comment that related_user made to generate this activity. Its parent is the comment field.')
    experience = models.ForeignKey('Experience', on_delete=CASCADE, blank=True, null=True)
    playlist = models.ForeignKey('Playlist', on_delete=CASCADE, blank=True, null=True)
    experience_stack = models.ForeignKey('ExperienceStack', on_delete=CASCADE, blank=True, null=True)
    like = models.ForeignKey('Like', on_delete=CASCADE, blank=True, null=True)

    @property
    def related_user_profile_picture_thumbnail(self):
        if self.related_user is None:
            return None
        profile_pic = self.related_user.profile_picture_thumbnail
        if bool(profile_pic):
            return profile_pic.url
        return None

    @property
    def related_image(self):
        related_content = None
        if self.post is not None:
            related_content = self.post
        if self.experience is not None:
            related_content = self.experience
        if self.playlist is not None:
            related_content = self.playlist

        if related_content is not None:
            file = related_content.thumbnail
            if file is not None:
                try:
                    return file.url
                except:
                    pass
        return None

    @property
    def related_user_username(self):
        if self.related_user is None:
            return None
        return self.related_user.username

    @property
    def follows_viewer(self):
        if self.related_user is None:
            return None
        return self.related_user.follows.contains(self.user)

    @property
    def followed_by_viewer(self):
        if self.related_user is None:
            return None
        return self.user.follows.contains(self.related_user)

    @property
    def message(self):
        '''Potential push notification title'''
        return ActivityUtils.get_activity_message(self)

    @property
    def is_tag_type(self) -> bool:
        return int(self.type) in [
            ActivityType.MENTIONED_EXPERIENCE.value,
            ActivityType.MENTIONED_PLAYLIST.value,
            ActivityType.MENTIONED_EXPERIENCE_STACK.value,
            ActivityType.MENTIONED_POST.value,
            ActivityType.MENTIONED_COMMENT.value,
        ]

    @property
    def is_like_type(self) -> bool:
        return int(self.type) in [
            ActivityType.LIKED_EXPERIENCE.value,
            ActivityType.LIKED_PLAYLIST.value,
            ActivityType.LIKED_EXPERIENCE_STACK.value,
            ActivityType.LIKED_POST.value,
            ActivityType.LIKED_COMMENT.value,
        ]

    @property
    def is_comment_type(self) -> bool:
        return int(self.type) in [
            ActivityType.COMMENTED_EXPERIENCE.value,
            ActivityType.COMMENTED_PLAYLIST.value,
            ActivityType.COMMENTED_EXPERIENCE_STACK.value,
            ActivityType.COMMENTED_POST.value,
            ActivityType.COMMENTED_COMMENT.value,
        ]

    @property
    def is_content_interaction_type(self) -> bool:
        return int(self.type) in [
            ActivityType.ACCEPTED_EXPERIENCE.value,
            ActivityType.COMPLETED_EXPERIENCE.value,
            ActivityType.ACCEPTED_PLAYLIST.value,
            ActivityType.COMPLETED_PLAYLIST.value,
        ]

    @property
    def is_follow_type(self) -> bool:
        return int(self.type) in [
            ActivityType.FOLLOW_ACCEPTED.value,
            ActivityType.FOLLOW_NEW.value,
            ActivityType.FOLLOW_REQUEST.value,
        ]

    # override
    def clean(self):
        super().clean()
        if self.related_user is None:
            raise ValidationError('related_user not provided on activity')
        match ActivityType(self.type):
            case ActivityType.RECEIVED_MESSAGE:
                if (self.message is None):
                    raise ValidationError(
                        'message not provided on a RECEIVED_MESSAGE')

            case ActivityType.MENTIONED_EXPERIENCE:
                if (self.experience is None):
                    raise ValidationError(
                        'experience not provided on a MENTIONED_PLAYLIST_POST')
            case ActivityType.MENTIONED_PLAYLIST:
                if (self.playlist is None):
                    raise ValidationError(
                        'playlist or not provided on a MENTIONED_PLAYLIST')
            case ActivityType.MENTIONED_EXPERIENCE_STACK:
                if (self.experience_stack is None):
                    raise ValidationError(
                        'experience_stack not provided on a MENTIONED_EXPERIENCE_STACK')
            case ActivityType.MENTIONED_POST:
                if (self.post is None):
                    raise ValidationError(
                        'post not provided on a MENTIONED_POST')
            case ActivityType.MENTIONED_COMMENT:
                if (self.comment is None):
                    raise ValidationError(
                        'comment not provided on a MENTIONED_COMMENT')

            case ActivityType.LIKED_EXPERIENCE:
                if (self.experience is None):
                    raise ValidationError(
                        'experience not provided on a LIKED_EXPERIENCE')
            case ActivityType.LIKED_PLAYLIST:
                if (self.playlist is None):
                    raise ValidationError(
                        'playlist or not provided on a LIKED_PLAYLIST')
            case ActivityType.LIKED_EXPERIENCE_STACK:
                if (self.experience_stack is None):
                    raise ValidationError(
                        'experience_stack not provided on a LIKED_EXPERIENCE_STACK')
            case ActivityType.LIKED_POST:
                if (self.post is None):
                    raise ValidationError(
                        'post not provided on a LIKED_POST')
            case ActivityType.LIKED_COMMENT:
                if (self.comment is None):
                    raise ValidationError(
                        'comment not provided on a LIKED_COMMENT')

            case ActivityType.COMMENTED_EXPERIENCE:
                if (self.experience is None):
                    raise ValidationError(
                        'experience not provided on a COMMENTED_EXPERIENCE')
                if (self.related_comment is None):
                    raise ValidationError(
                        'related_comment not provided on a COMMENTED_EXPERIENCE')
            case ActivityType.COMMENTED_PLAYLIST:
                if (self.playlist is None):
                    raise ValidationError(
                        'playlist or not provided on a COMMENTED_PLAYLIST')
                if (self.related_comment is None):
                    raise ValidationError(
                        'related_comment not provided on a COMMENTED_PLAYLIST')
            case ActivityType.COMMENTED_EXPERIENCE_STACK:
                if (self.experience_stack is None):
                    raise ValidationError(
                        'experience_stack not provided on a COMMENTED_EXPERIENCE_STACK')
                if (self.related_comment is None):
                    raise ValidationError(
                        'related_comment not provided on a COMMENTED_EXPERIENCE_STACK')
            case ActivityType.COMMENTED_POST:
                if (self.post is None):
                    raise ValidationError(
                        'post not provided on a COMMENTED_POST')
                if (self.related_comment is None):
                    raise ValidationError(
                        'related_comment not provided on a COMMENTED_POST')
            case ActivityType.COMMENTED_COMMENT:
                if (self.comment is None):
                    raise ValidationError(
                        'comment not provided on a COMMENTED_COMMENT')
                if (self.related_comment is None):
                    raise ValidationError(
                        'related_comment not provided on a COMMENTED_COMMENT')

            case ActivityType.ACCEPTED_EXPERIENCE:
                if (self.experience is None):
                    raise ValidationError(
                        'post not provided on a ACCEPTED_EXPERIENCE')
            case ActivityType.COMPLETED_EXPERIENCE:
                if (self.experience is None):
                    raise ValidationError(
                        'comment not provided on a COMPLETED_EXPERIENCE')
            case ActivityType.ACCEPTED_PLAYLIST:
                if (self.playlist is None):
                    raise ValidationError(
                        'playlist not provided on a ACCEPTED_PLAYLIST')
            case ActivityType.COMPLETED_PLAYLIST:
                if (self.experience is None):
                    raise ValidationError(
                        'playlist not provided on a COMPLETED_PLAYLIST')

            case ActivityType.FOLLOW_NEW:
                pass
            case ActivityType.FOLLOW_ACCEPTED:
                pass
            case ActivityType.FOLLOW_REQUEST:
                pass

            case ActivityType.ADDED_TO_YOUR_PLAYLIST:
                if (self.playlist is None):
                    raise ValidationError(
                        'playlist not provided on a ADDED_TO_YOUR_PLAYLIST')
            case ActivityType.REMOVED_FROM_PLAYLIST:
                if (self.playlist is None):
                    raise ValidationError(
                        'playlist not provided on a REMOVED_FROM_PLAYLIST')
            case ActivityType.ADDED_YOUR_EXPERIENCE_TO_PLAYLIST:
                if (self.experience is None):
                    raise ValidationError(
                        'experience not provided on a ADDED_YOUR_EXPERIENCE_TO_PLAYLIST')
                if (self.playlist is None):
                    raise ValidationError(
                        'playlist not provided on a ADDED_YOUR_EXPERIENCE_TO_PLAYLIST')


    def __str__(self):
        return f"{self.user} {self.created_at.strftime('%Y-%m-%d %H:%M')}"
