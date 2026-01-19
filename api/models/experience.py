import logging
from django.core.validators import MaxValueValidator, MinValueValidator
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.indexes import GistIndex
from django.contrib.postgres.fields import ArrayField
from django.db.models import (
    Avg,
    BooleanField,
    CASCADE,
    CharField,
    CheckConstraint,
    Count,
    DateTimeField,
    F,
    FloatField,
    ForeignKey,
    IntegerField,
    ManyToManyField,
    OneToOneField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    Q,
    QuerySet,
    TextField,
)
from lf_service.category import LifeFrameCategoryService

from api.enums import (
    Difficulty,
    Publicity,
)
from api.models.abstract.soft_delete_model import SoftDeleteModel
from api.models.abstract.file_content import FileContent
from api.models.abstract.publicly_viewable import PubliclyViewable
from api.models.abstract.start_end_time import StartEndTimeModel
# Importing models separately avoids circular import
from api.models.abstract.admin_mentions_html import AdminMentionsHtml
from api.models.badge_plan import BadgePlan
from api.models.attachment import Attachment
from api.models.comment import Comment
from api.utils.mentioning import MentionUtils
from api.validators import non_zero_validator


logger = logging.getLogger('app')

class ExperienceLatLong(gis_models.Model):
    experience = OneToOneField('api.Experience', on_delete=CASCADE, related_name='latlong')
    # https://docs.djangoproject.com/en/4.2/ref/contrib/gis/model-api/#pointfield
    # Note: GeoDjango documentation says Point(longitude, latitude), in that order
    # Note: srid=4326 ensures the point is stored using WGS84,
    #       the most common coordinate system for latitude and longitude.
    point = gis_models.PointField(null=True, blank=True, srid=4326)
    class Meta:
        indexes = [
            GistIndex(fields=["point"]),
        ]

class Experience(SoftDeleteModel, FileContent, StartEndTimeModel, PubliclyViewable, AdminMentionsHtml):

    def __init__(self, *args, **kwargs):
        self.search_similarity: float | None = None
        return super().__init__(*args, **kwargs)

    created_by = ForeignKey('User',
        on_delete=CASCADE, related_name='created_experiences')
    created_at = DateTimeField(auto_now_add=True)

    name = CharField(max_length=250, db_index=True)
    categories = ArrayField(
        PositiveIntegerField(validators=[non_zero_validator]),
        blank=True,
        null=True,
        help_text='LifeFrame IDs')
    description = CharField(max_length=100000, blank=True, null=True)
    mentions = ManyToManyField('User', blank=True,
        related_name='experience_mentioned_in')
    difficulty = PositiveSmallIntegerField(choices=Difficulty.choices, blank=True, null=True)
    visibility = PositiveSmallIntegerField(choices=Publicity.choices, default=Publicity.PUBLIC)
    shared_with = ManyToManyField('User', blank=True,
        related_name='shared_experiences')
    star_ratings = ManyToManyField('User', through='ExperienceStarRating',
        blank=True, related_name='experience_star_ratings_experiences')
    cost_ratings = ManyToManyField('User', through='ExperienceCostRating',
        blank=True, related_name='experience_cost_ratings_experiences')
    likes = ManyToManyField('User', through='Like',
        related_name='experience_likes')

    latitude = FloatField(db_index=True, blank=True, null=True,
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)])
    longitude = FloatField(db_index=True, blank=True, null=True,
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)])
    location = CharField(max_length=500, blank=True, null=True,
        help_text='Human-readable Google Maps API result')

    phone = CharField(max_length=20, blank=True, null=True)
    custom_categories = ManyToManyField('CustomCategory', blank=True,
        related_name='experiences')
    categories_need_manual_review = BooleanField(default=False,
        help_text='If checked, ' + \
            'this Experience has unknown requested categories from the import script and needs manual attention ' + \
            'OR a requested category matches more than 1 LifeFrame category and needs a human to decide')

    # Web Links
    website = CharField(max_length=2048, blank=True, null=True)
    reservation_link = CharField(max_length=2048, blank=True, null=True)
    menu_link = CharField(max_length=2048, blank=True, null=True)
    purchase_link = CharField(max_length=2048, blank=True, null=True)

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


    # TODO: Remove these field when we know we won't import from google sheets or old db anymore
    geo_tag = CharField(max_length=500, blank=True, null=True, db_index=True,
        help_text="This field will be removed soon")
    qc_reviewed = BooleanField(default=False,
        help_text="This field will be removed soon")
    cost_needs_review = BooleanField(default=False,
        help_text="This field will be removed soon")
    cost_description = TextField(blank=True, null=True,
        help_text="This field will be removed soon")
    original_id = IntegerField(blank=True, null=True, db_index=True,
        help_text="This field will be removed soon")
    original_data = TextField(blank=True, null=True,
        help_text="This field will be removed soon")

    @property
    def attachments(self) -> QuerySet[Attachment]:
        return Attachment.objects.filter(experience=self)

    @property
    def badge_plans(self) -> QuerySet[BadgePlan]:
        return BadgePlan.objects.filter(experience=self)


    @property
    def comments(self) -> QuerySet[Comment]:
        return Comment.objects.filter(experience=self, parent=None)


    def calc_average_cost_rating(self, set_and_save: bool = False) -> float:
        ratings_manager = self.cost_ratings.through.objects
        ratings = ratings_manager.filter(experience=self)
        value = ratings.aggregate(Avg('rating'))['rating__avg']
        if set_and_save and self.average_cost_rating != value:
            self.average_cost_rating = value
            self.save()
        return value

    def calc_average_star_rating(self, set_and_save: bool = False) -> float:
        ratings_manager = self.star_ratings.through
        ratings = ratings_manager.objects.filter(experience=self)
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
        value = Comment.objects.filter(experience=self).count()
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

        logger.info(f'Aggregate changes to experience {self.id}: {changes}')
        if len(changes) > 0:
            self.save()

    def __str__(self):
        name = self.name
        if name is None or name.strip() == '':
            name = '<no name>'
        return f'{name} (ID: {self.id})'

    # override
    def save(self, *args, **kwargs):
        creating = self.id is None
        if self.website is not None:
            self.website = self.website.strip()
            if self.website == '':
                self.website = None
        # If the categories changed sync up with lifeframe
        pre_save_category_ids: list[int]
        should_update_mentions: bool
        if creating:
            pre_save_category_ids = []
            should_update_mentions = True
        else:
            base_manager =\
                Experience.all_objects if self.is_deleted else Experience.objects
            exp_values = base_manager \
                .filter(pk=self.pk) \
                .values('categories', 'description',)
            pre_save_category_ids = exp_values[0]['categories'] or []
            pre_save_description = exp_values[0]['description']
            should_update_mentions = pre_save_description != self.description
        pre_save_category_ids = set(pre_save_category_ids or [])
        super(Experience, self).save(*args, **kwargs)
        post_save_category_ids = set(self.categories or [])
        if pre_save_category_ids != post_save_category_ids:
            self._sync_with_lf_from_experience_change(
                list(pre_save_category_ids),
                list(post_save_category_ids))
            self._sync_playlist_aggregated_categories()

        # Handle mentions
        if self.description is None:
            self.mentions.set([])
        elif should_update_mentions:
            mentioned_users = MentionUtils.verified_users_mentioned_in_text(self.description)
            self.mentions.set(mentioned_users)

    # override
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self._sync_with_lf_after_deleting_experience()
        self._sync_playlist_aggregated_categories()


    def _sync_playlist_aggregated_categories(self):
        for pl in self.playlists.all():
            pl.update_aggregated_categories()


    def _sync_with_lf_from_experience_change(self,
        pre_save_category_ids: list[int],
        post_save_category_ids: list[int]):
        if settings.TESTING:
            return
        others_have_pre_save_categories =\
            True if len(pre_save_category_ids) == 0 else \
            Experience.objects.exclude(pk=self.id) \
                .annotate(
                    total_count=Count('categories'),
                    matching_count=Count(
                        'categories',
                        filter=Q(categories=pre_save_category_ids))) \
                .filter(total_count=len(pre_save_category_ids)) \
                .filter(matching_count=len(pre_save_category_ids)) \
                .distinct() \
                .exists()

        others_have_post_save_categories =\
            True if len(post_save_category_ids) == 0 else\
            Experience.objects.exclude(pk=self.id) \
                .annotate(
                    total_count=Count('categories'),
                    matching_count=Count(
                        'categories',
                        filter=Q(categories=post_save_category_ids))) \
                .filter(total_count=len(post_save_category_ids)) \
                .filter(matching_count=len(post_save_category_ids)) \
                .distinct() \
                .exists()

        if not others_have_pre_save_categories:
            LifeFrameCategoryService() \
                .mark_has_no_content(pre_save_category_ids)
        if not others_have_post_save_categories:
            LifeFrameCategoryService() \
                .mark_has_content(post_save_category_ids)


    def _sync_with_lf_after_deleting_experience(self):
        if (settings.TESTING or
            self.categories is None or
            not self.categories):
            return
        ids_to_notify_remove = []
        for id in self.categories:
            other_experiences_use_category = Experience.objects \
                .exclude(pk=self.id) \
                .filter(categories__overlap=[id]) \
                .exists()
            if not other_experiences_use_category:
                ids_to_notify_remove.append(id)
        if len(ids_to_notify_remove) > 0:
            try:
                LifeFrameCategoryService().mark_has_no_content(ids_to_notify_remove)
            except:
                msg = 'Experience delete():\n' + \
                    f'Could not mark_has_no_content for experience with id {self.id}'
                logger.error(msg)


    class Meta:
        constraints = [
            CheckConstraint(
                check= Q(start_time=None) | Q(end_time=None) | Q(start_time__lte=F('end_time')),
                name='start_experience_before_end')
        ]
