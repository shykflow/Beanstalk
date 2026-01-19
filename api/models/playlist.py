import logging
from django.db.models import (
    Avg,
    CASCADE,
    CharField,
    CheckConstraint,
    DateTimeField,
    FloatField,
    ForeignKey,
    F,
    ManyToManyField,
    Q,
    QuerySet,
    PositiveIntegerField,
    PositiveSmallIntegerField,
)
from django.contrib.postgres.fields import ArrayField

from api.enums import Publicity
from api.models.abstract.admin_mentions_html import AdminMentionsHtml
from api.models.abstract.file_content import FileContent
from api.models.abstract.publicly_viewable import PubliclyViewable
from api.models.abstract.soft_delete_model import SoftDeleteModel
from api.models.abstract.start_end_time import StartEndTimeModel
from api.models.attachment import Attachment
from api.models.comment import Comment
from api.utils.mentioning import MentionUtils
from api.validators import non_zero_validator

logger = logging.getLogger('app')


class Playlist(
    SoftDeleteModel,
    FileContent,
    StartEndTimeModel,
    PubliclyViewable,
    AdminMentionsHtml):

    def __init__(self, *args, **kwargs):
        self.search_similarity: float | None = None
        return super().__init__(*args, **kwargs)

    name = CharField(max_length=250, db_index=True)
    description = CharField(max_length=100000, blank=True, null=True)
    mentions = ManyToManyField('User', blank=True, related_name='playlists_mentioned_in')
    created_at = DateTimeField(auto_now_add=True)
    created_by = ForeignKey('User',
        on_delete=CASCADE, related_name='created_playlists')
    editability = PositiveSmallIntegerField(choices=Publicity.choices, default=Publicity.PRIVATE)
    visibility = PositiveSmallIntegerField(choices=Publicity.choices, default=Publicity.PUBLIC)
    start = DateTimeField(blank=True, null=True)
    end = DateTimeField(blank=True, null=True)
    experiences = ManyToManyField('Experience', related_name='playlists')
    star_ratings = ManyToManyField('User', through='PlaylistStarRating',
        blank=True, related_name='playlist_star_rating_playlists')
    cost_ratings = ManyToManyField('User', through='PlaylistCostRating',
        blank=True, related_name='playlist_cost_ratings_playlists')
    aggregated_categories = ArrayField(
        PositiveIntegerField(validators=[non_zero_validator]),
        blank=True,
        null=True,
        help_text='LifeFrame IDs')
    likes = ManyToManyField('User', through='Like', related_name='playlist_likes')

    @property
    def comments(self) -> QuerySet[Comment]:
        return Comment.objects.filter(playlist=self, parent=None)


    # Aggregates
    total_likes = PositiveIntegerField(default=0)
    total_comments = PositiveIntegerField(default=0)
    total_accepts = PositiveIntegerField(default=0)
    total_completes = PositiveIntegerField(default=0)
    total_reviews = PositiveIntegerField(default=0)
    average_star_rating = FloatField(default=None,
        blank=True, null=True, db_index=True)
    average_cost_rating = FloatField(default=None,
        blank=True, null=True, db_index=True)


    def calc_average_cost_rating(self, set_and_save: bool = False) -> float:
        ratings_manager = self.cost_ratings.through.objects
        ratings = ratings_manager.filter(playlist=self)
        value = ratings.aggregate(Avg('rating'))['rating__avg']
        if set_and_save and self.average_cost_rating != value:
            self.average_cost_rating = value
            self.save()
        return value

    def calc_average_star_rating(self, set_and_save: bool = False) -> float:
        ratings_manager = self.star_ratings.through
        ratings = ratings_manager.objects.filter(playlist=self)
        value = ratings.aggregate(Avg('rating'))['rating__avg']
        if set_and_save and self.average_star_rating != value:
            self.average_star_rating = value
            self.save()
        return value

    def calc_total_likes(self, set_and_save: bool = False) -> int:
        value = self.likes.all().count()
        if set_and_save and self.total_likes != value:
            self.total_likes = value
            self.save()
        return value

    def calc_total_comments(self, set_and_save: bool = False) -> int:
        value = Comment.objects.filter(playlist=self).count()
        if set_and_save and self.total_comments != value:
            self.total_comments = value
            self.save()
        return value

    def calc_total_accepts(self, set_and_save: bool = False) -> int:
        value = self.users_accepted.count()
        if set_and_save and self.total_accepts != value:
            self.total_accepts = value
            self.save()
        return value

    def calc_total_completes(self, set_and_save: bool = False) -> int:
        value = self.users_completed.count()
        if set_and_save and self.total_completes != value:
            self.total_completes = value
            self.save()
        return value

    def calc_total_reviews(self, set_and_save: bool = False) -> int:
        cost_ratings_qs = self.cost_ratings.all()
        star_ratings_qs = self.star_ratings.all()
        value = (cost_ratings_qs | star_ratings_qs).distinct().count()
        if set_and_save and self.total_reviews != value:
            self.total_reviews = value
            self.save()
        return value

    def calc_and_save_all_aggregates(self):
        """
        Recalculates all aggregated fields and saves to the database
        """
        changes = []
        average_cost_rating = self.calc_average_cost_rating()
        average_star_rating = self.calc_average_star_rating()
        total_likes = self.calc_total_likes()
        total_comments = self.calc_total_comments()
        total_accepts = self.calc_total_accepts()
        total_completes = self.calc_total_completes()
        total_reviews = self.calc_total_reviews()
        if self.average_cost_rating != average_cost_rating:
            self.average_cost_rating = average_cost_rating
            changes.append('average_cost_rating')
        if self.average_star_rating != average_star_rating:
            self.average_star_rating = average_star_rating
            changes.append('average_star_rating')
        if self.total_likes != total_likes:
            self.total_likes = total_likes
            changes.append('total_likes')
        if self.total_comments != total_comments:
            self.total_comments = total_comments
            changes.append('total_comments')
        if self.total_accepts != total_accepts:
            self.total_accepts = total_accepts
            changes.append('total_accepts')
        if self.total_completes != total_completes:
            self.total_completes = total_completes
            changes.append('total_completes')
        if self.total_reviews != total_reviews:
            self.total_reviews = total_reviews
            changes.append('total_reviews')
        logger.info(f'Aggregate changes to playlist {self.id}: {changes}')
        if len(changes) > 0:
            self.save()

    def update_aggregated_categories(self):
        results = self.experiences.values_list('categories')
        categories_lists: list[list[int]] = [x[0] for x in results]
        categories: list[int] = []
        for categories_list in categories_lists:
            if categories_list is None or len(categories_list) == 0:
                continue
            categories += categories_list
        categories = list(set(categories))
        self.aggregated_categories = categories
        self.save()

    # override
    def save(self, *args, **kwargs):
        super(Playlist, self).save(*args, **kwargs)
        if self.description is None:
            self.mentions.set([])
        else:
            mentioned_users = MentionUtils.verified_users_mentioned_in_text(self.description)
            self.mentions.set(mentioned_users)


    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            CheckConstraint(
                check= Q(start_time=None) | Q(end_time=None) | Q(start_time__lte=F('end_time')),
                name='start_playlist_before_end')
        ]
