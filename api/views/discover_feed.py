import random
import uuid
import logging

from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.core.cache import cache
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from django.db.models import (
    BooleanField,
    Case,
    Q,
    QuerySet,
    Value,
    When,
)
from django.db.models.functions import Upper
from django.http import Http404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.models import (
    Playlist,
    CategoryMapping,
    Experience,
    NearYouMapping,
    Post,
    User,
)
from api.pagination import AppPageNumberPagination, get_page_size_from_request
from api.serializers.category_mapping import CategoryMappingSerializer
from api.serializers.experience import ExperienceViewSerializer
from api.serializers.near_you_mapping import (
    NearYouMappingSerializer,
    NearYouMappingFromExperienceSerializer,
)
from api.serializers.playlist import PlaylistViewSerializer
from api.serializers.post import PostViewSerializer
from api.serializers.user import UserViewSerializer
from api.utils import unique_objects
from api.utils.discover_feed import DiscoverFeedContinuation
from api.utils.earth import EarthHelper
from api.utils.life_frame_category import (
    CategoryGetter,
    lf_categories_to_mappings_dict,
)
from api.utils.measure_time_diff import MeasureTimeDiff
from lf_service.models import Category, CategoryGroup

logger = logging.getLogger('app')

class DiscoverFeedViewSet(viewsets.ViewSet):
    verbose_timing = True

    def list(self, request: Request, *args, **kwargs) -> Response:
        QUERY_LIMITS: dict[str, int] = settings.DISCOVER_QUERY_LIMITS
        if QUERY_LIMITS['CATEGORIES_ONLY']:
            with MeasureTimeDiff(
                label='GET - Discover Feed - categories only'):
                response=self.categories_only_list(request, QUERY_LIMITS)
        else:
            with MeasureTimeDiff(
                label='GET - Discover Feed - all items'):
                response=self.all_items_list(request, QUERY_LIMITS)
        return response

    def categories_only_list(
            self,
            request: Request,
            QUERY_LIMITS: dict[str, int]
        ) -> Response:
        user: User = request.user
        continuation_key: str = request.query_params.get('continuation', '').strip()
        if continuation_key == '':
            continuation_key = uuid.uuid4()
        continuation = DiscoverFeedContinuation(
            user=user,
            token=continuation_key)
        continuation.page += 1

        category_getter = CategoryGetter()

        if continuation.page == 1:
            with MeasureTimeDiff(
                label='Categories - Get Popular',
                depth=1):
                popular_response = category_getter.popular_categories()
                # popular_category_groups = popular_response['category_groups']
                popular_categories: list[Category] = popular_response['categories']
                logger.info(f'- Popular Received: {len(popular_categories)}')
                continuation.popular_category_ids = [c.id for c in popular_categories]
                continuation.cached_categories += popular_categories

        on_page_one_not_enough_content = continuation.page == 1 and \
            len(continuation.cached_categories) < QUERY_LIMITS['CATEGORIES']

        if on_page_one_not_enough_content or continuation.page == 2:
            with MeasureTimeDiff(
                label="Categories - Get Relevant",
                depth=1):
                relevant_response = category_getter.relevant(
                    life_frame_id=user.life_frame_id,
                    limit=100)
                # continuation.cached_category_groups = relevant_response['category_groups']
                relevant_categories: list[Category] = relevant_response['categories']
                logger.info(f'- Relevant Received: {len(relevant_categories)}')
                continuation.cached_categories += [
                    c
                    for c in relevant_categories
                    if c.id not in continuation.popular_category_ids
                ]

        continuation.unique_cached_categories()

        # Endless random after the user runs out of popular or relevant
        if len(continuation.cached_categories) < QUERY_LIMITS['CATEGORIES']:
            with MeasureTimeDiff(
                label='Categories - Get Random',
                depth=1):
                random_response = category_getter.random(
                    limit=100)
                logger.info(f'- Random Received: {len(random_response)}')
                continuation.cached_categories += random_response
            continuation.unique_cached_categories()

        # This method will only ever fill in the categories, but the `all_items_list`
        # method and this method are meant to be interchangeable, so this also needs
        # to return all the fields.
        data = {
            'continuation': str(continuation.token),
            'categories': [],
            'experiences': [],
            'playlists': [],
            'posts': [],
        }

        with MeasureTimeDiff(
            label='Categories - Build what to send',
            depth=1):
            categories_to_send: list[Category] = []
            for _ in range(QUERY_LIMITS['CATEGORIES']):
                if len(continuation.cached_categories) == 0:
                    break
                # Pop a random category from the cache
                category = random.choice(continuation.cached_categories)
                continuation.cached_categories.remove(category)

                categories_to_send.append(category)

        category_mappings_dict = lf_categories_to_mappings_dict(categories_to_send)
        category_mappings_to_send: list[CategoryMapping] = []
        for item in category_mappings_dict.items():
            mapping = item[1]
            category_mappings_to_send.append(mapping)

        with MeasureTimeDiff(
            label='Categories - Cache',
            depth=1):
            # Ensure all the categories needed are in the cache with one query
            category_getter.list([cm.category_id for cm in category_mappings_to_send])

        with MeasureTimeDiff(
            label='Category Mappings - Serialize',
            depth=1):
            serializer = CategoryMappingSerializer(category_mappings_to_send, many=True)
            data['categories'] = list(serializer.data)

        logger.info(f'- Sending {len(data["categories"])} Categories')
        continuation.debug_print()
        continuation.set_cache()
        return Response(data)

    def all_items_list(
            self,
            request: Request,
            QUERY_LIMITS: dict[str, int]
        ) -> Response:
        user: User = request.user
        continuation_key: str = request.query_params.get('continuation', '').strip()
        if continuation_key == '':
            continuation_key = uuid.uuid4()
        shuffled: bool = request.query_params.get('shuffled', 'false').lower() == 'true'
        with_images_str: str = request.query_params.get('with_images', 'true')
        if with_images_str not in ['true', 'false']:
            msg = 'with_images must be true or false'
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)
        with_images = with_images_str == 'true'
        continuation = DiscoverFeedContinuation(user=user, token=continuation_key)

        category_getter = CategoryGetter()
        available_categories: list[Category] = []

        with MeasureTimeDiff(
            label="Categories - Get Relevant",
            enabled=self.verbose_timing,
            depth=1):
            relevant_response = category_getter.relevant(
                life_frame_id=user.life_frame_id,
                limit=100)
        continuation.cached_category_groups = relevant_response['category_groups']
        continuation.cached_categories = relevant_response['categories']
        relevant_category_ids = [c.id for c in continuation.cached_categories]

        popular_category_groups: list[CategoryGroup] = []
        popular_categories: list[Category] = []
        with MeasureTimeDiff(
            label='Categories - Get Popular',
            enabled=self.verbose_timing,
            depth=1):
            popular_response = category_getter.popular_categories()
            popular_category_groups = popular_response['category_groups'][:3]
            popular_categories = popular_response['categories'][:3]
            available_categories = [
                c for c in
                unique_objects(continuation.cached_categories, popular_categories)
                if c.id not in continuation.popular_category_ids
            ]

        if QUERY_LIMITS['CATEGORIES_ONLY']:
            experiences_qs = Experience.objects.none()
            playlists_qs = Playlist.objects.none()
            posts_qs = Post.objects.none()
        else:
            experiences_qs = Experience.objects.all()
            playlists_qs = Playlist.objects.all()
            posts_qs = Post.objects.all()

        experiences_qs = experiences_qs \
            .exclude(created_by=user)
        playlists_qs = playlists_qs \
            .exclude(created_by=user)
        posts_qs = posts_qs \
            .filter(Q(experience__isnull=False) | Q(playlist__isnull=False)) \
            .exclude(created_by=user)

        if len(continuation.cached_categories) > 0 and not shuffled:
            experiences_qs = experiences_qs \
                .filter(categories__overlap=relevant_category_ids)
            playlists_qs = playlists_qs \
                .filter(aggregated_categories__overlap=relevant_category_ids)
            posts_qs = Post.objects \
                .filter(Q(experience__in=experiences_qs) | Q(playlist__in=playlists_qs))

        experiences_qs = experiences_qs \
            .exclude(id__in=continuation.sent_experiences)
        playlists_qs = playlists_qs \
            .exclude(id__in=continuation.sent_playlists)
        posts_qs = posts_qs \
            .exclude(id__in=continuation.sent_posts)

        # User Blocks
        # If doing this subquery ends up being slower, try
        # blocked_user_ids = list(user.blocks.values_list('id', flat=True))
        blocked_user_ids_qs = user.blocks.values_list('id', flat=True)
        experiences_qs = experiences_qs \
            .exclude(created_by__in=blocked_user_ids_qs) \
            .exclude(created_by__blocks=user)
        playlists_qs = playlists_qs \
            .exclude(created_by__in=blocked_user_ids_qs) \
            .exclude(created_by__blocks=user)
        posts_qs = posts_qs \
            .exclude(created_by__in=blocked_user_ids_qs) \
            .exclude(created_by__blocks=user)

        if shuffled:
            experiences_qs = experiences_qs.order_by('?')
            playlists_qs = playlists_qs.order_by('?')
            posts_qs = posts_qs.order_by('?')
        elif with_images:
            experiences_qs = experiences_qs.exclude(highlight_image='')
            playlists_qs = playlists_qs.exclude(highlight_image='')
            posts_qs = posts_qs.exclude(highlight_image='')
        # without images
        else:
            experiences_qs = experiences_qs.filter(highlight_image='')
            playlists_qs = playlists_qs.filter(highlight_image='')
            posts_qs = posts_qs.filter(highlight_image='')

        data = {
            'continuation': str(continuation.token),
            'categories': [],
            'experiences': [],
            'playlists': [],
            'posts': [],
        }

        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label='Categories - Build what to send',
            depth=1):
            categories_to_send: list[Category] = []
            for i in range(QUERY_LIMITS['CATEGORIES']):
                if len(available_categories) > 0:
                    category = random.choice(available_categories)
                    categories_to_send.append(category)
                    available_categories.remove(category)
                    continuation.popular_category_ids.append(category.id)
            category_mappings_dict = lf_categories_to_mappings_dict(categories_to_send)
            category_mappings_to_send: list[CategoryMapping] = []
            for item in category_mappings_dict.items():
                mapping = item[1]
                category_mappings_to_send.append(mapping)

        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label='Categories - Cache',
            depth=1):
            # Ensure all the categories needed are in the cache with one query
            category_getter.list([cm.category_id for cm in category_mappings_to_send])

        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label='Category Mappings - Serialize',
            depth=1):
            serializer = CategoryMappingSerializer(category_mappings_to_send, many=True)
            data['categories'] = list(serializer.data)

        request_context = {'request': request}

        experiences_qs = experiences_qs \
            .prefetch_related("created_by")
        playlists_qs = playlists_qs \
            .prefetch_related("created_by")
        posts_qs = posts_qs \
            .prefetch_related("created_by")

        experiences_qs = experiences_qs[:QUERY_LIMITS['EXPERIENCES']]
        playlists_qs = playlists_qs[:QUERY_LIMITS['PLAYLISTS']]
        posts_qs = posts_qs[:QUERY_LIMITS['POSTS']]

        # Execute database calls
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label='Experiences - Query',
            depth=1):
            experiences = list(experiences_qs)
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label='Playlists - Query',
            depth=1):
            playlists = list(playlists_qs)
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label='Posts - Query',
            depth=1):
            posts = list(posts_qs)

        # Serialize content and add to continuation
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label='Experiences - Serialize',
            depth=1):
            serializer = ExperienceViewSerializer(
                experiences,
                many=True,
                context=request_context)
            data['experiences'] += serializer.data
            continuation.sent_experiences += [e.id for e in experiences]
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label='Playlists - Serialize',
            depth=1):
            serializer = PlaylistViewSerializer(
                playlists,
                many=True,
                context=request_context)
            data['playlists'] += serializer.data
            continuation.sent_playlists += [pl.id for pl in playlists]
        with MeasureTimeDiff(
            enabled=self.verbose_timing,
            label='Experience Posts - Serialize',
            depth=1):
            serializer = PostViewSerializer(
                posts,
                many=True,
                context=request_context)
            data['posts'] += serializer.data
            continuation.sent_posts += [p.id for p in posts]

        # continuation.debug_print()
        continuation.set_cache()
        return Response(data)

    @action(detail=False, methods=['get'])
    def search(self, request: Request) -> Response:
        with MeasureTimeDiff(
            label='Total Search Time',
            enabled=self.verbose_timing):
            response = self._search(request)
        return response

    def _search(self, request: Request) -> Response:
        user: User = request.user
        phrase: str = request.query_params.get('phrase', '').strip()
        if phrase == '':
            return Response(status=status.HTTP_400_BAD_REQUEST)
        query_params = request.query_params
        with_categories = query_params.get('with_categories', 'true').strip() == 'true'
        with_users = query_params.get('with_users', 'true').strip() == 'true'
        relevant = query_params.get('relevant', 'true').strip() == 'true'
        exclude_request_user_created = query_params.get('exclude_user_content', 'false').strip() == 'true'

        similarity_multiplier: float = 1.0
        phrase = phrase.upper()
        words = [s for s in phrase.split() if s != '']
        goal_items_to_send = 30
        items: list[User|Experience|Playlist|Category] = []

        base_user_qs: QuerySet[User] = User.objects.exclude(is_active=False)
        base_experience_qs: QuerySet[Experience] = Experience.objects.all()
        base_playlist_qs: QuerySet[Playlist] = Playlist.objects.all()

        # User Blocks
        # If doing this subquery ends up being slower, try
        # blocked_user_ids = list(user.blocks.values_list('id', flat=True))
        blocked_user_ids_qs = user.blocks.values_list('id', flat=True)
        base_user_qs = base_user_qs \
            .exclude(id__in=blocked_user_ids_qs) \
            .exclude(blocks=user)
        base_experience_qs = base_experience_qs \
            .exclude(created_by__in=blocked_user_ids_qs) \
            .exclude(created_by__blocks=user)
        base_playlist_qs = base_playlist_qs \
            .exclude(created_by__in=blocked_user_ids_qs) \
            .exclude(created_by__blocks=user)

        if exclude_request_user_created:
            base_user_qs = base_user_qs \
                .exclude(pk=user.pk)
            base_experience_qs = base_experience_qs \
                .exclude(created_by=user)
            base_playlist_qs = base_playlist_qs \
                .exclude(created_by=user)

        # Search for user's content directly if there was high match on the user's username
        users: list[User] = []
        with MeasureTimeDiff(
            label='Search Users by username',
            enabled=self.verbose_timing,
            depth=1):
            user_qs: QuerySet[User] = base_user_qs \
                .annotate(search_similarity=TrigramSimilarity(
                    'username',
                    phrase)) \
                .filter(search_similarity__gt=0.5) \
                .order_by('-search_similarity')[:8]
            users = [x for x in user_qs]
            if with_users:
                items += users

        if len(users) > 0:
            similarity_multiplier = similarity_multiplier * 0.95
        for user in users:
            if len(items) < goal_items_to_send:
                goal_remaining = goal_items_to_send - len(items)
                with MeasureTimeDiff(
                    label='Get Experiences by found users',
                    enabled=self.verbose_timing,
                    depth=1):
                    previously_gathered_ids = [
                        item.id
                        for item in items
                        if type(item) is Experience]
                    experience_qs = base_experience_qs \
                        .filter(created_by=user) \
                        .order_by('-created_at') \
                        .exclude(id__in=previously_gathered_ids) \
                        [:goal_remaining]
                    for experience in experience_qs:
                        experience.search_similarity = user.search_similarity * similarity_multiplier
                        items.append(experience)
            if len(items) < goal_items_to_send:
                goal_remaining = goal_items_to_send - len(items)
                with MeasureTimeDiff(
                    label='Get Playlists by found users',
                    enabled=self.verbose_timing,
                    depth=1):
                    playlist_qs = base_playlist_qs \
                        .filter(created_by=user) \
                        .order_by('-created_at')
                    playlist_qs = playlist_qs[:goal_remaining]
                    for playlist in playlist_qs:
                        playlist.search_similarity = user.search_similarity * similarity_multiplier
                        items.append(playlist)

        if len(users) > 0:
            similarity_multiplier = similarity_multiplier / 2

        # Add experiences and playlists that name match the search
        if len(items) < goal_items_to_send:
            # Add experiences that match
            with MeasureTimeDiff(
                label='Search Experiences by name',
                enabled=self.verbose_timing,
                depth=1):
                previously_gathered_ids = [
                    item.id
                    for item in items
                    if type(item) is Experience]
                experience_qs = base_experience_qs \
                    .annotate(search_similarity=TrigramSimilarity(
                        Upper('name'),
                        phrase)) \
                    .filter(search_similarity__gt=0.3) \
                    .exclude(id__in=previously_gathered_ids) \
                    .order_by('-search_similarity') \
                    [:goal_items_to_send - len(items)]
                experiences = list(experience_qs)
                if len(experiences) < goal_items_to_send - len(items):
                    previously_gathered_ids += [
                        experience.id
                        for experience in experiences
                    ]
                    goal_remaining = goal_items_to_send - len(items) - len(experiences)
                    search_q = Q()
                    for word in words:
                        search_q &= Q(name__icontains=word)
                    experience_qs = base_experience_qs \
                    .filter(search_q) \
                    .exclude(id__in=previously_gathered_ids) \
                    [:goal_remaining]
                    experiences_contains_all = list(experience_qs)
                    for experience in experiences_contains_all:
                        # Manual annotate
                        experience.search_similarity = 1
                    experiences += experiences_contains_all
                for experience in experiences:
                    experience.search_similarity *= similarity_multiplier
                items += experiences

        if len(items) < goal_items_to_send:
            # Add playlists that match
            with MeasureTimeDiff(
                label='Search Playlists by name',
                enabled=self.verbose_timing,
                depth=1):
                previously_gathered_ids = [
                    item.id
                    for item in items
                    if type(item) is Playlist]
                playlist_qs = base_playlist_qs \
                    .annotate(search_similarity=TrigramSimilarity(
                        Upper('name'),
                        phrase)) \
                    .filter(search_similarity__gt=0.3) \
                    .exclude(id__in=previously_gathered_ids) \
                    .order_by('-search_similarity') \
                    [:goal_items_to_send - len(items)]
                playlists = list(playlist_qs)
                if len(playlists) < goal_items_to_send - len(items):
                    previously_gathered_ids += [
                        playlist.id
                        for playlist in playlists]
                    goal_remaining = goal_items_to_send - len(items) - len(playlists)
                    search_q = Q()
                    for word in words:
                        search_q &= Q(name__icontains=word)
                    playlist_qs = base_playlist_qs \
                        .filter(search_q) \
                        .exclude(id__in=previously_gathered_ids) \
                    [:goal_remaining]
                    playlists_contains_all:list['Playlist'] = list(playlist_qs)
                    for playlist in playlists_contains_all:
                        # Manual annotate
                        playlist.search_similarity = 1
                    playlists += playlists_contains_all
                for playlist in playlists:
                    playlist.search_similarity *= similarity_multiplier
                items += playlists

        # Add experiences and playlists that are in matched category names
        if len(items) < goal_items_to_send:
            similarity_multiplier = similarity_multiplier / 2
            search_categories: list[Category] = []
            search_category_ids: list[int] = []
            category_getter = CategoryGetter()
            with MeasureTimeDiff(
                label='Search Categories on LifeFrame (with cache if the same search)',
                enabled=self.verbose_timing,
                depth=1):
                search_categories = category_getter.searched_categories(
                    phrase=phrase,
                    threshold=0.5)
            if with_categories:
                # Filter out categories that have already been gathered
                previously_gathered_ids = [
                    item.id
                    for item in items
                    if type(item) is Category]
                search_categories = [
                    c
                    for c in search_categories
                    if c.id not in previously_gathered_ids]
                search_category_ids = [c.id for c in search_categories]
                items += search_categories

            if len(search_categories) > 0:
                with MeasureTimeDiff(
                    label='Get popular categories',
                    enabled=self.verbose_timing,
                    depth=1):
                    popular_response = category_getter.popular_categories()
                popular_category_groups = popular_response['category_groups']
                popular_categories = popular_response['categories']
                popular_category_ids = [x.id for x in popular_categories]
                # Note: Popular Categories are those that people have been interacting
                #       with the most in LifeFrame.
                # Find Experiences that have Categories that were searched for.
                # Find Playlists that have those Experiences.
                # Mark if a resulting Experience has a popular Category.
                # Mark if a resulting Playlist has a popular Experience.
                # Attach the highest matched Category.search_similarity to each
                # resulting Experience and Playlist

                with MeasureTimeDiff(
                    label='Get content in searched categories',
                    enabled=self.verbose_timing,
                    depth=1):
                    previously_gathered_ids = [
                        item.id
                        for item in items
                        if type(item) is Experience]
                    experiences_in_search_categories = base_experience_qs \
                        .filter(categories__overlap=search_category_ids)

                    experience_qs: QuerySet[Experience]
                    if len(items) > goal_items_to_send:
                        experience_qs = Experience.objects.none()
                    else:
                        experience_qs = Experience.objects \
                            .filter(id__in=experiences_in_search_categories) \
                            .exclude(id__in=previously_gathered_ids) \
                            .annotate(popular=Case(
                                When(
                                    categories__overlap=popular_category_ids,
                                    then=Value(True)),
                                default=Value(False),
                                output_field=BooleanField())) \
                            .order_by('-popular') \
                            .prefetch_related('created_by') \
                            [:goal_items_to_send - len(items)]

                    experiences: list[Experience] = list(experience_qs)
                    for experience in experiences:
                        experience.search_similarity = 0
                        for category in search_categories:
                            if category.id in experience.categories:
                                # Order by search similarity but un-weight them so they
                                # probably show up lower in the results list
                                experience.search_similarity = category.search_similarity * similarity_multiplier
                                if not experience.popular:
                                    experience.search_similarity = experience.search_similarity / 2
                                break
                    items += experiences

                    if len(items) > goal_items_to_send:
                        playlist_qs = Playlist.objects.none()
                    else:
                        playlists_in_search_categories = base_playlist_qs \
                            .filter(experiences__in=experiences_in_search_categories)
                        playlist_qs = Playlist.objects \
                            .filter(id__in=playlists_in_search_categories) \
                            .annotate(popular=Case(
                                When(
                                    aggregated_categories__overlap=popular_category_ids,
                                    then=Value(True)),
                                default=Value(False),
                                output_field=BooleanField())) \
                            .order_by('-popular') \
                            .prefetch_related('experiences', 'created_by')
                        previously_gathered_ids = [
                            item.id
                            for item in items
                            if type(item) is Playlist]
                        playlist_qs = playlist_qs \
                            .exclude(id__in=previously_gathered_ids) \
                            [:goal_items_to_send - len(items)]

                    playlists: list[Playlist] = list(playlist_qs)
                    for playlist in playlists:
                        experience_category_ids: list[int] = []
                        experience: Experience
                        for experience in playlist.experiences.all():
                            if experience.categories is not None:
                                experience_category_ids += experience.categories
                        experience_category_ids = list(set(experience_category_ids))
                        playlist.search_similarity = 0
                        for category in search_categories:
                            if category.id in experience_category_ids:
                                # Order by search similarity but un-weight them so they
                                # probably show up lower in the results list
                                playlist.search_similarity = category.search_similarity * similarity_multiplier
                                if not playlist.popular:
                                    playlist.search_similarity = playlist.search_similarity / 2
                                break
                    items += playlists

        items.sort(key=lambda x: x.search_similarity, reverse=True)
        data = []
        with MeasureTimeDiff(
            label='Serialize',
            enabled=self.verbose_timing,
            depth=1):
            categories = [
                item
                for item in items
                if type(item) is Category]
            categories_to_mapping_dicts = lf_categories_to_mappings_dict(categories)
            request_context = {'request': request}
            for item in items:
                if type(item) is User:
                    serializer = UserViewSerializer(item)
                elif type(item) is Category:
                    mapping = categories_to_mapping_dicts[item]
                    serializer = CategoryMappingSerializer(mapping)
                elif type(item) is Experience:
                    serializer = ExperienceViewSerializer(item, context=request_context)
                elif type(item) is Playlist:
                    serializer = PlaylistViewSerializer(item, context=request_context)
                else:
                    continue
                serialized = serializer.data
                serialized['search_similarity'] = item.search_similarity
                data.append(serialized)
        return Response(data)

    @action(detail=False, methods=['get'])
    def near(self, request: Request) -> Response:
        with MeasureTimeDiff(
            label='GET near',
            enabled=self.verbose_timing):
            response = self._near(request)
        return response

    def _near(self, request: Request) -> Response:
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        if latitude is None or longitude is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            latitude = round(float(latitude), 4)
            longitude = round(float(longitude), 4)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if not EarthHelper.valid_coordinates(latitude, longitude):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        radius_miles = request.query_params.get('radius', '25.0')
        try:
            radius_miles = round(float(radius_miles), 3)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        # Note: GeoDjango documentation says Point(longitude, latitude), in that order
        # Note: srid=4326 ensures the point is stored using WGS84,
        #       the most common coordinate system for latitude and longitude.
        lat_long = Point(longitude, latitude, srid=4326)
        exp_qs = Experience.objects \
            .annotate(distance_from_point=Distance('latlong__point', lat_long)) \
            .filter(distance_from_point__lte=D(mi=radius_miles))
        search_phrase = request.query_params.get('search', '').strip().upper()
        if search_phrase != '':
            trigram_search_annotation = TrigramSimilarity(Upper('name'), search_phrase)
            exp_qs = exp_qs \
                .annotate(search_similarity=trigram_search_annotation) \
                .filter(search_similarity__gt=0.1) \
                .order_by('-search_similarity')
        else:
            exp_qs = exp_qs \
                .order_by('distance_from_point')
        page_size = get_page_size_from_request(request, 10)
        paginator = AppPageNumberPagination(page_size=page_size)
        page = paginator.paginate_queryset(exp_qs, request)
        request_context = {'request': request}
        serializer = ExperienceViewSerializer(page, many=True, context=request_context)
        return paginator.get_paginated_response(serializer.data)


    @action(detail=False, methods=['get'])
    def near_you_mapping(self, request: Request) -> Response:
        with MeasureTimeDiff(
            label='GET near_you_mapping',
            enabled=self.verbose_timing):
            response = self._near_you_mapping(request)
        return response

    def _near_you_mapping(self, request: Request) -> Response:
        latitude = request.query_params.get('latitude', '').strip()
        longitude = request.query_params.get('longitude', '').strip()
        earth_helper = EarthHelper()
        if latitude == '' or longitude == '':
            near_you_mapping = self._get_near_you_mapping(
                latitude=None, longitude=None, earth_helper=earth_helper)
            if near_you_mapping is None:
                raise Http404
            serializer = NearYouMappingSerializer(near_you_mapping)
            return Response(serializer.data)
        try:
            latitude = round(float(latitude), 4)
            longitude = round(float(longitude), 4)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if not EarthHelper.valid_coordinates(latitude, longitude):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        radius_miles = 25.0
        # Note: GeoDjango documentation says Point(longitude, latitude), in that order
        # Note: srid=4326 ensures the point is stored using WGS84,
        #       the most common coordinate system for latitude and longitude.
        geo_location = Point(longitude, latitude, srid=4326)
        random_near_experience_with_image = Experience.objects \
            .exclude(highlight_image='') \
            .annotate(distance_from_point=Distance('latlong__point', geo_location)) \
            .filter(distance_from_point__lte=D(mi=radius_miles)) \
            .order_by('?') \
            .first()
        if random_near_experience_with_image is None:
            near_you_mapping = self._get_near_you_mapping(
                latitude, longitude, earth_helper)
            if near_you_mapping is None:
                raise Http404
            serializer = NearYouMappingSerializer(near_you_mapping)
        else:
            serializer = NearYouMappingFromExperienceSerializer(
                random_near_experience_with_image)
        return Response(serializer.data)


    def _get_near_you_mapping(self, latitude: float | None,
        longitude: float | None, earth_helper: EarthHelper) -> NearYouMapping | None:
        """
        Attempts to find a `NearYouMapping` object "near" the given `latitude`
        and `longitude`, where "near" is within the NearYouMapping's `radius`.

        Returns `None` if it does not find one or if the given `latitude` or
        `longitude` are `None`.
        """
        # TODO: Convert the mapping's latitude / longitude to a PointField()
        if latitude is not None and longitude is not None:
            base_qs = NearYouMapping.objects.all()
            near_mappings: list[NearYouMapping] = []
            for mapping in base_qs:
                if not mapping.radius:
                    continue
                max_lat_difference = earth_helper.distance_to_latitude(
                    mapping.radius)
                min_allowed_lat = mapping.latitude - max_lat_difference
                max_allowed_lat = mapping.latitude + max_lat_difference
                if not min_allowed_lat <= latitude <= max_allowed_lat:
                    continue
                max_lng_difference = earth_helper.distance_to_longitude(
                    mapping.radius)
                min_allowed_lng = mapping.longitude - max_lng_difference
                max_allowed_lng = mapping.longitude + max_lng_difference
                if not min_allowed_lng <= longitude <= max_allowed_lng:
                    continue
                near_mappings.append(mapping)
            if near_mappings:
                near_mappings.sort(key=lambda x: x.radius)
                return near_mappings[0]
        return NearYouMapping.objects.filter(is_default=True).first()
