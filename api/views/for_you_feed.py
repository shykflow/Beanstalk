import random
import uuid

from django.conf import settings
from django.utils import timezone
from django.db.models import (
    BooleanField,
    Case,
    Count,
    Exists,
    F,
    OuterRef,
    Subquery,
    Q,
    QuerySet,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.response import Response

from api.models import (
    Comment,
    Experience,
    Like,
    ExperienceCompletion,
    Playlist,
    PlaylistCompletion,
    Post,
    User,
)
from api.serializers.experience import ExperienceViewSerializer
from api.serializers.playlist import PlaylistViewSerializer
from api.serializers.post import PostViewSerializer
from api.utils.for_you_feed import (
    ForYouFeedContinuation,
    ForYouCategories,
)
from api.utils.life_frame_category import CategoryGetter
from api.utils.measure_time_diff import MeasureTimeDiff


class ForYouFeedViewSet(viewsets.ViewSet):
    """
    This class heavily uses queryset `overlap` and `contains`

    `overlap` says to get any record that has at least one presented value.
    https://docs.djangoproject.com/en/4.2/ref/contrib/postgres/fields/#overlap

    `contains` says to get any record that has all presented values.
    https://docs.djangoproject.com/en/4.2/ref/contrib/postgres/fields/#contains
    """
    verbose_timing = False
    verbose_timing_left_column_size = 11


    def list(self, request: Request) -> Response:
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label='GET - For You Feed'):
            query_params = request.query_params
            query_mode_str = query_params.get('mode', '').strip()

            allowed_item_types = [
                'experiences',
                'lists',
                'posts',
            ]
            item_types_str: str = query_params.get('types', ','.join(allowed_item_types)).strip()
            item_types = item_types_str.split(',')
            for item_type in item_types:
                if item_type not in allowed_item_types:
                    return Response(
                        f'{item_type} is not an allowed type',
                        status=status.HTTP_400_BAD_REQUEST)

            continuation_key: str = query_params.get('continuation', '').strip()
            on_page_one = continuation_key == ''
            if continuation_key == '':
                continuation_key = uuid.uuid4()

            continuation = ForYouFeedContinuation(
                user=request.user,
                token=continuation_key)

            video_only: bool = query_params.get('video_only', 'false').strip() == 'true'

            #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=11)
            """
            The mobile app used to send "follow_only" instead of "query_mode",
            this adapts the param follow_only => query_mode
            """
            if query_mode_str == '':
                if query_params.get('follow_only', 'false').strip() == 'true':
                    query_mode_str = 'follow'
                else:
                    query_mode_str = 'global'
            #! END BACK COMPAT (just delete this section)

            match (query_mode_str):
                case 'follow':
                    response = self.follow_feed(
                        request=request,
                        item_types=item_types,
                        on_page_one=on_page_one,
                        video_only=video_only,
                        continuation=continuation)
                case 'global':
                    response = self.global_feed(
                        request=request,
                        item_types=item_types,
                        on_page_one=on_page_one,
                        video_only=video_only,
                        continuation=continuation)
                case _:
                    return Response(
                        '`query_mode` param is required and must be either ' + \
                        '`follow` or `global`',
                        status=status.HTTP_400_BAD_REQUEST)
        if self.verbose_timing:
            continuation.debug_print()
        return response


    def follow_feed(self,
            request: Request,
            item_types: 'list[str]',
            on_page_one: bool,
            video_only: bool,
            continuation: ForYouFeedContinuation) -> tuple[Response, ForYouFeedContinuation]:
        request_user: User = request.user

        QUERY_LIMITS: dict[str, int] = settings.FOR_YOU_QUERY_LIMITS
        data = {
            'continuation': str(continuation.token),
            'items': [],
        }
        categories = self._prepare_categories(
            continuation,
            popular_only=on_page_one,
            user=request_user)

        if self.verbose_timing:
            categories.debug_print()

        qs_dict = self._initialize_querysets(
            request_user,
            continuation,
            item_types,
            video_only=video_only,
            annotate_seen=False)
        experiences_qs: QuerySet[Experience] = qs_dict['experiences']
        playlists_qs: QuerySet[Playlist] = qs_dict['playlists']
        posts_qs: QuerySet[Post] = qs_dict['posts']

        follows_qs = request_user.follows.all()

        experiences_qs = experiences_qs.filter(created_by__in=follows_qs)
        playlists_qs = playlists_qs.filter(created_by__in=follows_qs)
        posts_qs = posts_qs.filter(created_by__in=follows_qs)

        experiences_qs = experiences_qs \
            .order_by('-created_at')
        playlists_qs = playlists_qs \
            .order_by('-created_at')
        posts_qs = posts_qs \
            .order_by('-created_at')

        # Limits
        experiences_qs = experiences_qs[:QUERY_LIMITS['EXPERIENCES']]
        playlists_qs = playlists_qs[:QUERY_LIMITS['PLAYLISTS']]
        posts_qs = posts_qs[:QUERY_LIMITS['POSTS']]

        # Get content from DB
        experiences: list[Experience] = []
        playlists: list[Playlist] = []
        posts: list[Post] = []
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label=f'{"Experiences".ljust(self.verbose_timing_left_column_size)} - Query' \
                if self.verbose_timing \
                else '',
            depth=1):
            experiences = list(experiences_qs)
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label=f'{"Playlists".ljust(self.verbose_timing_left_column_size)} - Query' \
                if self.verbose_timing \
                else '',
            depth=1):
            playlists = list(playlists_qs)
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label=f'{"Posts".ljust(self.verbose_timing_left_column_size)} - Query' \
                if self.verbose_timing \
                else '',
            depth=1):
            posts = list(posts_qs)

        # Serialize content and add to continuation
        request_context = {'request': request}
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label=f'{"Experiences".ljust(self.verbose_timing_left_column_size)} - Serialize' \
                if self.verbose_timing \
                else '',
            depth=1):
            if len(experiences) > 0:
                serializer = ExperienceViewSerializer(
                    experiences,
                    many=True,
                    context=request_context,
                    num_sample_comments=QUERY_LIMITS['NUM_SAMPLE_COMMENTS'])
                data['items'] += serializer.data
                continuation.sent_experiences += [e.id for e in experiences]
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label=f'{"Playlists".ljust(self.verbose_timing_left_column_size)} - Serialize' \
                if self.verbose_timing \
                else '',
            depth=1):
            if len(playlists) > 0:
                serializer = PlaylistViewSerializer(
                    playlists,
                    many=True,
                    num_sample_comments=0,
                    context=request_context)
                data['items'] += serializer.data
                continuation.sent_playlists += [pl.id for pl in playlists]
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label=f'{"Posts".ljust(self.verbose_timing_left_column_size)} - Serialize' \
                if self.verbose_timing \
                else '',
            depth=1):
            if len(posts) > 0:
                serializer = PostViewSerializer(
                    posts,
                    many=True,
                    num_sample_comments=QUERY_LIMITS['NUM_SAMPLE_COMMENTS'],
                    context=request_context)
                data['items'] += serializer.data
                continuation.sent_posts += [p.id for p in posts]
        continuation.set_cache()
        return Response(data, status=status.HTTP_200_OK)


    def global_feed(self,
            request: Request,
            item_types: 'list[str]',
            on_page_one: bool,
            video_only: bool,
            continuation: ForYouFeedContinuation) -> tuple[Response, ForYouFeedContinuation]:
        request_user: User = request.user
        now = timezone.datetime.now(tz=timezone.utc)
        one_week_ago = now - timezone.timedelta(days=7)

        QUERY_LIMITS: dict[str, int] = settings.FOR_YOU_QUERY_LIMITS
        data = {
            'continuation': str(continuation.token),
            'items': [],
        }
        categories = self._prepare_categories(
            continuation,
            popular_only=on_page_one,
            user=request_user)

        if self.verbose_timing:
            categories.debug_print()

        qs_dict = self._initialize_querysets(
            request_user,
            continuation,
            item_types,
            video_only=video_only,
            annotate_seen=True)
        experiences_qs: QuerySet[Experience] = qs_dict['experiences']
        playlists_qs: QuerySet[Playlist] = qs_dict['playlists']
        posts_qs: QuerySet[Post] = qs_dict['posts']

        follows_qs = request_user.follows.all()

        experiences_q = Q(created_by__in=follows_qs)
        playlists_q = Q(created_by__in=follows_qs)
        posts_q = Q(created_by__in=follows_qs)
        relevant_or_popular_ids = [c.id for c in categories.relevant_or_popular]
        if len(categories.relevant_or_popular) > 0:
            experiences_q |= Q(
                categories__overlap=relevant_or_popular_ids)
            for cg in categories.relevant_or_popular_cgs:
                experiences_q |= Q(categories__contains=cg.categories)
            playlists_q |= Q(
                aggregated_categories__overlap=relevant_or_popular_ids)
            posts_q |= (
                    (
                        Q(experience__in=experiences_qs)
                        | Q(playlist__in=playlists_qs)
                    )
                & ~Q(highlight_image=''))

        experiences_qs = experiences_qs.filter(experiences_q)
        playlists_qs = playlists_qs.filter(playlists_q)
        posts_qs = posts_qs.filter(posts_q)

        # Has highlight_image
        experiences_qs = experiences_qs \
            .annotate(has_highlight_image=Case(
                When(
                    highlight_image='',
                    then=Value(False)),
                default=Value(True),
                output_field=BooleanField()))
        playlists_qs = playlists_qs \
            .annotate(has_highlight_image=Case(
                When(
                    highlight_image='',
                    then=Value(False)),
                default=Value(True),
                output_field=BooleanField()))
        posts_qs = posts_qs \
            .annotate(has_highlight_image=Case(
                When(
                    highlight_image='',
                    then=Value(False)),
                default=Value(True),
                output_field=BooleanField()))

        # Experiences
        experiences_recent_like_count_sub = Subquery(
            Like.objects \
                .filter(experience_id=OuterRef('pk')) \
                .filter(created_at__gte=one_week_ago) \
                .values('experience') \
                .annotate(recent_count=Count('pk')) \
                .values('recent_count'))
        experiences_recent_comment_count_sub = Subquery(
            Comment.objects \
                .filter(experience_id=OuterRef('pk')) \
                .filter(created_at__gte=one_week_ago) \
                .values('experience') \
                .annotate(recent_count=Count('pk')) \
                .values('recent_count'))
        experiences_recent_completion_count_sub = Subquery(
            ExperienceCompletion.objects \
                .filter(experience_id=OuterRef('pk')) \
                .filter(created_at__gte=one_week_ago) \
                .values('experience') \
                .annotate(recent_count=Count('pk')) \
                .values('recent_count'))
        experiences_qs = experiences_qs \
            .annotate(recent_like_count=experiences_recent_like_count_sub)
        experiences_qs = experiences_qs \
            .annotate(recent_comment_count=experiences_recent_comment_count_sub)
        experiences_qs = experiences_qs \
            .annotate(recent_completion_count=experiences_recent_completion_count_sub)
        experiences_qs = experiences_qs \
            .annotate(order_score=Coalesce(
                F('recent_like_count') + \
                    F('recent_comment_count') + \
                    F('recent_completion_count'),
                0))

        # Playlists
        playlists_recent_like_count_sub = Subquery(
            Like.objects \
                .filter(playlist_id=OuterRef('pk')) \
                .filter(created_at__gte=one_week_ago) \
                .values('playlist') \
                .annotate(recent_count=Count('pk')) \
                .values('recent_count'))
        playlists_recent_comment_count_sub = Subquery(
            Comment.objects \
                .filter(playlist_id=OuterRef('pk')) \
                .filter(created_at__gte=one_week_ago) \
                .values('playlist') \
                .annotate(recent_count=Count('pk')) \
                .values('recent_count'))
        playlist_recent_completion_count_sub = Subquery(
            PlaylistCompletion.objects \
                .filter(playlist_id=OuterRef('pk')) \
                .filter(created_at__gte=one_week_ago) \
                .values('playlist') \
                .annotate(recent_count=Count('pk')) \
                .values('recent_count'))
        playlists_qs = playlists_qs \
            .annotate(recent_like_count=playlists_recent_like_count_sub)
        playlists_qs = playlists_qs \
            .annotate(recent_comment_count=playlists_recent_comment_count_sub)
        playlists_qs = playlists_qs \
            .annotate(recent_completion_count=playlist_recent_completion_count_sub)
        playlists_qs = playlists_qs \
            .annotate(order_score=Coalesce(
                F('recent_like_count') + \
                    F('recent_comment_count') + \
                    F('recent_completion_count'),
                0))

        # Posts
        posts_recent_like_count_sub = Subquery(
            Like.objects \
                .filter(post_id=OuterRef('pk')) \
                .filter(created_at__gte=one_week_ago) \
                .values('post') \
                .annotate(recent_count=Count('pk')) \
                .values('recent_count'))
        posts_recent_comment_count_sub = Subquery(
            Comment.objects \
                .filter(post_id=OuterRef('pk')) \
                .filter(created_at__gte=one_week_ago) \
                .values('post') \
                .annotate(recent_count=Count('pk')) \
                .values('recent_count'))
        posts_qs = posts_qs \
            .annotate(recent_like_count=posts_recent_like_count_sub)
        posts_qs = posts_qs \
            .annotate(recent_comment_count=posts_recent_comment_count_sub)
        posts_qs = posts_qs \
            .annotate(order_score=Coalesce(
                F('recent_like_count') + \
                    F('recent_comment_count'),
                0))

        # Order by
        experiences_qs = experiences_qs \
            .order_by('seen', '-has_highlight_image', '-order_score')
        playlists_qs = playlists_qs \
            .order_by('seen', '-has_highlight_image', '-order_score')
        posts_qs = posts_qs \
            .order_by('seen', '-has_highlight_image', '-order_score')

        # Limits
        experiences_qs = experiences_qs[:QUERY_LIMITS['EXPERIENCES']]
        playlists_qs = playlists_qs[:QUERY_LIMITS['PLAYLISTS']]
        posts_qs = posts_qs[:QUERY_LIMITS['POSTS']]

        # Get content from DB
        experiences: list[Experience] = []
        playlists: list[Playlist] = []
        posts: list[Post] = []
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label=f'{"Experiences".ljust(self.verbose_timing_left_column_size)} - Query' \
                if self.verbose_timing \
                else '',
            depth=1):
            experiences = list(experiences_qs)
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label=f'{"Playlists".ljust(self.verbose_timing_left_column_size)} - Query' \
                if self.verbose_timing \
                else '',
            depth=1):
            playlists = list(playlists_qs)
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label=f'{"Posts".ljust(self.verbose_timing_left_column_size)} - Query' \
                if self.verbose_timing \
                else '',
            depth=1):
            posts = list(posts_qs)

        # Serialize content and add to continuation
        request_context = {'request': request}
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label=f'{"Experiences".ljust(self.verbose_timing_left_column_size)} - Serialize' \
                if self.verbose_timing \
                else '',
            depth=1):
            if len(experiences) > 0:
                serializer = ExperienceViewSerializer(
                    experiences,
                    many=True,
                    context=request_context,
                    num_sample_comments=QUERY_LIMITS['NUM_SAMPLE_COMMENTS'])
                data['items'] += serializer.data
                continuation.sent_experiences += [e.id for e in experiences]
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label=f'{"Playlists".ljust(self.verbose_timing_left_column_size)} - Serialize' \
                if self.verbose_timing \
                else '',
            depth=1):
            if len(playlists) > 0:
                serializer = PlaylistViewSerializer(
                    playlists,
                    many=True,
                    num_sample_comments=0,
                    context=request_context)
                data['items'] += serializer.data
                continuation.sent_playlists += [pl.id for pl in playlists]
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label=f'{"Posts".ljust(self.verbose_timing_left_column_size)} - Serialize' \
                if self.verbose_timing \
                else '',
            depth=1):
            if len(posts) > 0:
                serializer = PostViewSerializer(
                    posts,
                    many=True,
                    num_sample_comments=QUERY_LIMITS['NUM_SAMPLE_COMMENTS'],
                    context=request_context)
                data['items'] += serializer.data
                continuation.sent_posts += [p.id for p in posts]
        continuation.set_cache()
        random.shuffle(data['items'])
        return Response(data, status=status.HTTP_200_OK)


    def _prepare_categories(self,
            continuation: ForYouFeedContinuation,
            popular_only: bool,
            user: User,
            ) -> ForYouCategories:
        categories = ForYouCategories()
        category_getter = CategoryGetter()

        with MeasureTimeDiff(
            label=f'{"Categories".ljust(self.verbose_timing_left_column_size)} - Get Relevant' \
                if self.verbose_timing else '',
            enabled=self.verbose_timing,
            depth=1):
            if not popular_only and len(continuation.relevant_categories) == 0:
                relevant_response = category_getter.relevant(
                    life_frame_id=user.life_frame_id,
                    limit=10)
                continuation.relevant_category_groups = relevant_response['category_groups']
                continuation.relevant_categories = relevant_response['categories']
                continuation.set_cache()
                categories.set_relevant(continuation.relevant_categories)
                categories.set_relevant_cgs(continuation.relevant_category_groups)
        with MeasureTimeDiff(
            label=f'{"Categories".ljust(self.verbose_timing_left_column_size)} - Get Popular' \
                if self.verbose_timing else '',
            enabled=self.verbose_timing,
            depth=1):
            popular_response = category_getter.popular_categories()
            popular_cgs = popular_response['category_groups']
            popular = popular_response['categories']
            categories.set_popular(popular)
            categories.set_popular_cgs(popular_cgs)
        return categories


    def _initialize_querysets(
            self,
            request_user: User,
            continuation: ForYouFeedContinuation,
            item_types: 'list[str]',
            video_only: bool,
            annotate_seen: bool) -> dict[str, QuerySet]:
        experiences_qs: QuerySet[Experience]
        playlists_qs: QuerySet[Playlist]
        posts_qs: QuerySet[Post]
        if 'experiences' in item_types:
            experiences_qs = Experience.objects.all()
        else:
            experiences_qs = Experience.objects.none()
        if 'lists' in item_types:
            playlists_qs = Playlist.objects.all()
        else:
            playlists_qs = Playlist.objects.none()
        if 'posts' in item_types:
            posts_qs = Post.objects.all()
        else:
            posts_qs = Post.objects.none()

        # Don't send repeats
        experiences_qs = experiences_qs \
            .exclude(id__in=continuation.sent_experiences)
        playlists_qs = playlists_qs \
            .exclude(id__in=continuation.sent_playlists)
        posts_qs = posts_qs \
            .exclude(id__in=continuation.sent_posts)

        # Don't send users their own content
        experiences_qs = experiences_qs \
            .exclude(created_by=request_user)
        playlists_qs = playlists_qs \
            .exclude(created_by=request_user)
        posts_qs = posts_qs \
            .exclude(created_by=request_user)

        # Don't send items from users who are blocked
        # If doing this subquery ends up being slower, try
        # blocked_user_ids = list(user.blocks.values_list('id', flat=True))
        blocked_user_ids_qs = request_user.blocks \
            .values_list('id', flat=True)
        experiences_qs = experiences_qs \
            .exclude(created_by__in=blocked_user_ids_qs) \
            .exclude(created_by__blocks=request_user)
        playlists_qs = playlists_qs \
            .exclude(created_by__in=blocked_user_ids_qs) \
            .exclude(created_by__blocks=request_user)
        posts_qs = posts_qs \
            .exclude(created_by__in=blocked_user_ids_qs) \
            .exclude(created_by__blocks=request_user)

        if video_only:
            experiences_qs = experiences_qs \
                .exclude(video__in=('', None))
            playlists_qs = playlists_qs \
                .exclude(video__in=('', None))
            posts_qs = posts_qs \
                .exclude(video__in=('', None))

        # Don't show posts about content created by users who are blocked
        posts_qs = posts_qs \
            .exclude(playlist__created_by__in=blocked_user_ids_qs) \
            .exclude(experience__created_by__in=blocked_user_ids_qs)

        # Prefetching related
        experiences_qs = experiences_qs \
            .prefetch_related(*[
                'created_by',
                'mentions',
                'custom_categories',
                'users_accepted',
                'users_completed',
            ])
        playlists_qs = playlists_qs \
            .prefetch_related(*[
                'created_by',
                'mentions',
                'users_accepted',
                'users_completed',
            ])
        posts_qs = posts_qs \
            .prefetch_related(*[
                'created_by',
                'mentions',
            ])

        # Annotate seen
        if annotate_seen:
            experiences_qs = experiences_qs \
                .annotate(seen=Exists(
                    User.seen_experiences.through.objects.filter(
                        experience_id=OuterRef('pk'),
                        user_id=request_user.pk)))
            playlists_qs = playlists_qs \
                .annotate(seen=Exists(
                    User.seen_playlists.through.objects.filter(
                        playlist_id=OuterRef('pk'),
                        user_id=request_user.pk)))
            posts_qs = posts_qs \
                .annotate(seen=Exists(
                    User.seen_posts.through.objects.filter(
                        post_id=OuterRef('pk'),
                        user_id=request_user.pk)))

        return {
            'experiences': experiences_qs,
            'playlists': playlists_qs,
            'posts': posts_qs,
        }
