import logging
from django.db.models import (
    CASCADE,
    CharField,
    DateTimeField,
    ForeignKey,
    ManyToManyField,
    OneToOneField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    Q,
    QuerySet,
    CheckConstraint,
)

from api.enums import Publicity
from api.models.abstract.admin_mentions_html import AdminMentionsHtml
from api.models.abstract.file_content import FileContent
from api.models.abstract.publicly_viewable import PubliclyViewable
from api.models.abstract.soft_delete_model import SoftDeleteModel
from api.models.comment import Comment
from api.utils.mentioning import MentionUtils

logger = logging.getLogger('app')

class Post(SoftDeleteModel, FileContent, PubliclyViewable, AdminMentionsHtml):
    name = CharField(max_length=250, db_index=True)
    text = CharField(max_length=100000)
    mentions = ManyToManyField('User', blank=True, related_name='posts_mentioned_in')

    created_by = ForeignKey('User', on_delete=CASCADE)
    created_at = DateTimeField(auto_now_add=True)
    # Intended to never be a tree, but be a queue
    parent = ForeignKey('Post', on_delete=CASCADE, blank=True, null=True)
    # Usually the final ExperiencePost will be the completion post
    experience_completion = OneToOneField('ExperienceCompletion',
        on_delete=CASCADE, blank=True, null=True)
    playlist_completion = OneToOneField('PlaylistCompletion',
        on_delete=CASCADE, blank=True, null=True)
    experience = ForeignKey('Experience', on_delete=CASCADE, blank=True, null=True)
    playlist = ForeignKey('Playlist', on_delete=CASCADE, blank=True, null=True)
    likes = ManyToManyField('User', through='Like', related_name='post_likes')
    visibility = PositiveSmallIntegerField(choices=Publicity.choices, default=Publicity.PUBLIC)

    # Aggregates
    total_likes = PositiveIntegerField(default=0)
    total_comments = PositiveIntegerField(default=0)

    @property
    def comments(self) -> QuerySet[Comment]:
        return Comment.objects.filter(post=self, parent=None)

    def calc_total_likes(self, set_and_save: bool = False) -> int:
        value = self.likes.all().count()
        if set_and_save and self.total_likes != value:
            self.total_likes = value
            self.save()
        return value

    def calc_total_comments(self, set_and_save: bool = False) -> int:
        value = Comment.objects.filter(post=self).count()
        if set_and_save and self.total_comments != value:
            self.total_comments = value
            self.save()
        return value

    def calc_and_save_all_aggregates(self):
        """
        Recalculates all aggregated fields and saves to the database
        """
        changes = []
        total_likes = self.calc_total_likes()
        total_comments = self.calc_total_comments()
        if self.total_likes != total_likes:
            self.total_likes = total_likes
            changes.append('total_likes')
        if self.total_comments != total_comments:
            self.total_comments = total_comments
            changes.append('total_comments')
        logger.info(f'Aggregate changes to post {self.id}: {changes}')
        if len(changes) > 0:
            self.save()

    def __str__(self):
        text = self.text[0:30]
        if text is None or text.strip() == '':
            text = '<no text>'
        else:
            if len(self.text) > 30:
                text += '...'
        return f'ID: {self.id}, Author: {self.created_by}, {text}'

    # override
    def save(self, *args, **kwargs):
        super(Post, self).save(*args, **kwargs)
        mentioned_users = MentionUtils.verified_users_mentioned_in_text(self.text)
        self.mentions.set(mentioned_users)

    class Meta:
        constraints = [
            CheckConstraint(
                check=Q(experience_completion=None) | Q(playlist_completion=None),
                name='only_complete_experience_or_playlist'),
            CheckConstraint(
                check=(~Q(experience_completion=None) & ~Q(experience=None)) | Q(experience_completion=None),
                name='experience_completions_must_have_experience'),
            CheckConstraint(
                check=(~Q(playlist_completion=None) & ~Q(playlist=None)) | Q(playlist_completion=None),
                name='playlist_completions_must_have_playlists'),
        ]
