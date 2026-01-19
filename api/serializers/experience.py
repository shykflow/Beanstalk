import logging
from rest_framework import serializers
from django.db.models import Count
from api.models import (
    Experience,
    ExperienceCostRating,
    ExperienceStarRating,
    Comment,
)
from api.serializers.attachment import AttachmentViewSerializer
from api.serializers.badge_plan import BadgePlanSerializer
from api.serializers.comment import CommentSerializer
from api.serializers.user import UserViewSerializer
from api.utils.life_frame_category import CategoryGetter

logger = logging.getLogger('app')

class ExperienceValidationSerializer(serializers.ModelSerializer):

    custom_categories = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False)

    def validate(self, data):
        self._sanitize_links(data)
        return super().validate(data)

    def _sanitize_links(self, data: dict[str, any]):
        fields = (
            'website',
            'reservation_link',
            'menu_link',
            'purchase_link',
        )
        for field in fields:
            value: str = data.get(field)
            if value is None:
                continue
            value = value.strip()
            if value == '':
                data[field] = None
            else:
                data[field] = value

    class Meta:
        model = Experience
        extra_kwargs = {
            'created_by': {
                'default': serializers.CurrentUserDefault(),
            }
        }
        fields = (
            'id',
            'created_at',
            'deleted_at',
            'name',
            'description',
            'categories',
            'custom_categories',
            'difficulty',
            'visibility',
            'created_by',
            'start_time',
            'end_time',
            'start_time_date_only',
            'end_time_date_only',
            'use_local_time',
            'latitude',
            'longitude',
            'location',
            'phone',
            'website',
            'reservation_link',
            'menu_link',
            'purchase_link',
        )


class ExperienceViewSerializer(serializers.ModelSerializer):
    def __init__(
        self,
        instance,
        num_sample_comments: int=0,
        *args,
        **kwargs):
        self.num_sample_comments = num_sample_comments
        super().__init__(instance, *args, **kwargs)
        if self.context.get('request') is None:
            raise Exception('Request not in context')

    badge_plans = BadgePlanSerializer(many=True, read_only=True)
    created_by = UserViewSerializer(read_only=True)
    accepted_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True)
    distance = serializers.SerializerMethodField()
    mentions = serializers.SerializerMethodField()
    model = serializers.SerializerMethodField()
    has_comments = serializers.SerializerMethodField()
    sample_comments = serializers.SerializerMethodField()
    user_accepted = serializers.SerializerMethodField()
    user_complete = serializers.SerializerMethodField()
    user_like = serializers.SerializerMethodField()
    user_star_rating = serializers.SerializerMethodField()
    custom_categories = serializers.SerializerMethodField()

    def get_distance(self, experience: Experience) -> float | None:
        if experience.latitude is None or experience.longitude is None:
            return None
        if hasattr(experience, 'distance') and experience.distance is not None:
            return experience.distance
        if hasattr(experience, 'distance_from_point') and experience.distance_from_point is not None:
            return experience.distance_from_point.mi

    def get_mentions(self, experience: Experience) -> list[dict]:
        # use prefetch_related on querysets to make this faster
        mentioned_users = list(m for m in experience.mentions.all())
        dicts = [
            { 'user_id': m.id, 'username': m.username }
            for m in mentioned_users
        ]
        return dicts

    def get_model(self, experience: Experience) -> str:
        return 'Experience'

    def get_has_comments(self, experience: Experience) -> bool:
        return experience.total_comments > 0

    def get_sample_comments(self, experience: Experience) -> list[map] :
        if self.num_sample_comments == 0: return []
        comments = experience.comments \
            .filter(parent=None) \
            .annotate(like_count=Count('likes')) \
            .order_by('-like_count', '-created_at') \
            [:self.num_sample_comments]
        request_context = {'request':  self.context.get('request')}
        serializer = CommentSerializer(
            comments,
            context=request_context,
            many=True)
        return serializer.data

    def get_user_accepted(self, experience: Experience) -> bool:
        request = self.context.get('request')
        return request.user.accepted_experiences.filter(pk=experience.pk).exists()

    def get_user_complete(self, experience: Experience) -> bool:
        request = self.context.get('request')
        return request.user.completed_experiences.filter(pk=experience.pk).exists()

    def get_user_like(self, experience: Experience) -> bool:
        request = self.context.get('request')
        return experience.likes.filter(pk=request.user.pk).exists()

    def get_user_star_rating(self, experience: Experience) -> int | None:
        request = self.context.get('request')
        rating: ExperienceStarRating = ExperienceStarRating.objects \
            .filter(experience=experience, created_by=request.user) \
            .first()
        if rating is None:
            return None
        return rating.rating

    def get_custom_categories(self, experience: Experience) -> list[str]:
        return [category.name for category in experience.custom_categories.all()]

    class Meta:
        model = Experience
        extra_kwargs = {
            'created_by': {
                'default': serializers.CurrentUserDefault(),
            }
        }
        fields = (
            'id',
            'created_at',
            'deleted_at',
            'accepted_at',
            'completed_at',
            'name',
            'description',
            'video',
            'highlight_image',
            'highlight_image_thumbnail',
            'categories',
            'custom_categories',
            'visibility',
            'created_by',
            'start_time',
            'end_time',
            'start_time_date_only',
            'end_time_date_only',
            'use_local_time',
            'badge_plans',
            'distance',
            'mentions',
            'model',
            'has_comments',
            'sample_comments',
            'user_accepted',
            'user_complete',
            'user_like',
            'user_star_rating',
            'website',
            'reservation_link',
            'menu_link',
            'purchase_link',
            'difficulty',
            'latitude',
            'longitude',
            'location',
            'phone',
            'website',

            # aggregates
            'average_cost_rating',
            'average_star_rating',
            'total_accepts',
            'total_comments',
            'total_completes',
            'total_likes',
            'total_reviews',
        )


class ExperienceDetailSerializer(ExperienceViewSerializer):
    attachments = AttachmentViewSerializer(many=True, read_only=True)
    category_objects = serializers.SerializerMethodField()
    user_cost_rating = serializers.SerializerMethodField()
    user_saved = serializers.SerializerMethodField()
    personal_bucket_list = serializers.SerializerMethodField()

    def get_category_objects(self, experience: Experience) -> list[dict]:
        category_ids = experience.categories
        if not bool(category_ids):
            return None
        categories_from_lifeframe, _ = CategoryGetter() \
            .list(category_ids)
        return [category.to_dict() for category in categories_from_lifeframe]

    def get_user_cost_rating(self, experience: Experience) -> int | None:
        request = self.context.get('request')
        rating: ExperienceCostRating = ExperienceCostRating.objects \
            .filter(experience=experience, created_by=request.user) \
            .first()
        if rating is None:
            return None
        return rating.rating

    def get_user_saved(self, experience: Experience) -> bool:
        request = self.context.get('request')
        return request.user.saved_experiences.filter(pk=experience.pk).exists()

    def get_personal_bucket_list(self, experience: Experience) -> bool:
        request = self.context.get('request')
        return request.user.bucket_list.filter(pk=experience.pk).exists()

    class Meta:
        model = Experience
        fields = ExperienceViewSerializer.Meta.fields + (
            'attachments',
            'user_cost_rating',
            'user_saved',
            'personal_bucket_list',
            'category_objects',
        )
