import logging
from django.db.models import (
    BooleanField,
    CASCADE,
    CharField,
    DateTimeField,
    ForeignKey,
    ManyToManyField,
    QuerySet,
    PositiveIntegerField,
)
from api.models.abstract.publicly_viewable import PubliclyViewable
from api.utils.mentioning import MentionUtils

logger = logging.getLogger('app')

class Comment(PubliclyViewable):
    created_by = ForeignKey('User', on_delete=CASCADE)
    created_at = DateTimeField(auto_now_add=True)
    edited = BooleanField(default=False, editable=False)
    text = CharField(max_length=2000)
    parent = ForeignKey('Comment', blank=True, null=True, on_delete=CASCADE)
    post = ForeignKey('Post', on_delete=CASCADE, blank=True, null=True,
        related_name='post_comments')
    playlist = ForeignKey('Playlist', on_delete=CASCADE, blank=True, null=True,
        related_name='playlist_comments')
    experience = ForeignKey('Experience', on_delete=CASCADE, blank=True, null=True,
        related_name='experience_comments')
    likes = ManyToManyField('User', through='Like',
        related_name='like_comments')
    mentions = ManyToManyField('User', blank=True,
        related_name='mention_comments')

    # Aggregates
    total_likes = PositiveIntegerField(default=0)
    total_comments = PositiveIntegerField(default=0)

    @property
    def comments(self) -> QuerySet['Comment']:
        return Comment.objects.filter(parent=self)

    @property
    def text_preview(self):
        if len(self.text) > 30:
            return self.text[:27] + '...'
        else:
            return self.text
    def calc_total_likes(self, set_and_save: bool = False) -> int:
        value = self.likes.all().count()
        if set_and_save and self.total_likes != value:
            self.total_likes = value
            self.save()
        return value

    def calc_total_comments(self, set_and_save: bool = False) -> int:
        value = Comment.objects.filter(parent=self).count()
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
        logger.info(f'Aggregate changes to comment {self.id}: {changes}')
        if len(changes) > 0:
            self.save()

    def __str__(self):
        return f'{self.created_by} | {self.text[:75]}{"" if len(self.text) < 75 else "..."}'

    # override
    def save(self, *args, **kwargs):
        if self.parent is not None and self.parent.parent is not None:
            raise Exception('Cannot create child comment of comment with parent')
        self.text = self.text.strip()
        super().save(*args, **kwargs)
        mentioned_users = MentionUtils.verified_users_mentioned_in_text(self.text)
        self.mentions.set(mentioned_users)
        from api.models import (
            Experience,
            Playlist,
            Post,
        )
        exp: Experience = self.experience
        pl: Playlist = self.playlist
        post: Post = self.post
        parent: Comment = self.parent
        if exp is not None:
            exp.calc_total_comments(set_and_save=True)
        if pl is not None:
            pl.calc_total_comments(set_and_save=True)
        if post is not None:
            post.calc_total_comments(set_and_save=True)
        if parent is not None:
            parent.calc_total_comments(set_and_save=True)

    def delete(self, *args, **kwargs):
        from api.models import (
            Experience,
            Playlist,
            Post,
        )
        exp: Experience = self.experience
        pl: Playlist = self.playlist
        post: Post = self.post
        parent: Comment = self.parent
        super_save_value = super().delete(*args, **kwargs)
        if exp is not None:
            exp.calc_total_comments(set_and_save=True)
        if pl is not None:
            pl.calc_total_comments(set_and_save=True)
        if post is not None:
            post.calc_total_comments(set_and_save=True)
        if parent is not None:
            parent.calc_total_comments(set_and_save=True)
        return super_save_value
