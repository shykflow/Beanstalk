from django.utils import timezone
from django.db.models.deletion import CASCADE, SET_NULL
from django.db import models

from api.enums import ActivityType
from api.utils.activity import ActivityUtils



class AggregateActivity(models.Model):
    class Meta:
        verbose_name_plural = 'Aggregate activities'

    '''Table to cache commonly used Activity data'''

    user = models.ForeignKey('api.User', on_delete=CASCADE)
    type = models.PositiveSmallIntegerField(choices=ActivityType.choices)
    count = models.IntegerField(default=1)
    post = models.ForeignKey('api.Post', on_delete=CASCADE, blank=True, null=True)
    comment = models.ForeignKey('api.Comment', on_delete=CASCADE, blank=True, null=True,
        help_text='The comment that all aggregated related_users commented on. It is the parent of all aggregated related_comments.')
    experience = models.ForeignKey('api.Experience', on_delete=CASCADE, blank=True, null=True)
    playlist = models.ForeignKey('api.Playlist', on_delete=CASCADE, blank=True, null=True)
    experience_stack = models.ForeignKey('api.ExperienceStack', on_delete=CASCADE, blank=True, null=True)
    # fields below are from the most recently seen activity
    related_comment = models.ForeignKey('api.Comment', on_delete=CASCADE, blank=True, null=True, related_name='aggregate_related_comment',
        help_text='The most recent aggregated comment. Its parent is the comment field.')
    created_at = models.DateTimeField(auto_now_add=True)
    related_time = models.DateTimeField(blank=True, null=True)
    related_user = models.ForeignKey('api.User', on_delete=SET_NULL, blank=True, null=True, related_name='last_related_user')

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
    def related_comment_text(self):
        if self.related_comment is not None:
            refined_comment = self.related_comment.text
            if refined_comment is not None:
                refined_comment = " ".join(refined_comment.split())
                if len(refined_comment) > 20:
                    return f' "{refined_comment[:20]}..."'
                else:
                    return refined_comment
        return None

    @property
    def message(self):
        return ActivityUtils.get_activity_message(self, item_count=self.count)

    def __str__(self):
        return f"{self.user} {self.count} {self.type}"
