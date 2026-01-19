import uuid
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import (
    BooleanField,
    Case,
    Q,
    QuerySet,
    When,
    Value,
)
from django.db.models.functions import Upper
from rest_framework import viewsets, status
from rest_framework.serializers import ModelSerializer
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from api.models.custom_category import CustomCategory

from lf_service import LifeFrameException, LifeFrameUserIDRequiredError
from lf_service.category import LifeFrameCategoryService

from api.models import (
    CategoryMapping,
    Experience,
    Playlist,
    User,
)
from api.serializers.category_mapping import CategoryMappingSerializer
from api.serializers.experience import ExperienceViewSerializer
from api.serializers.playlist import PlaylistViewSerializer
from api.serializers.user import UserViewSerializer
from api.utils.categories import (
    CategoryContentQuerysets,
    CategoryContentContinuation,
)
from api.utils.life_frame_category import (
    CategoryGetter,
    lf_categories_to_mappings_dict,
)
from api.utils.measure_time_diff import MeasureTimeDiff
from lf_service.models import Category
from sponsorship.models import (
    CategorySponsorship,
)

class CategoryViewSet(
        viewsets.GenericViewSet,
        viewsets.mixins.RetrieveModelMixin):

    queryset = CategoryMapping.objects.all()
    serializer_class = CategoryMappingSerializer


    @action(detail=False, methods=['get'])
    def from_category_id(self, request: Request) -> Response:
        pk = (request.query_params.get('id', '')).strip()
        if pk == '':
            return Response(status=status.HTTP_400_BAD_REQUEST)
        category_getter = CategoryGetter()
        category: Category
        try:
            category = category_getter.retrieve(pk)
        except LifeFrameException as e:
            return Response(status=e.status_code)
        mappings = lf_categories_to_mappings_dict([category])
        mapping: CategoryMapping = mappings[category]
        serializer = self.get_serializer(
            mapping,
            context={'with_related_counts': True})
        return Response(serializer.data)


    @action(detail=False, methods=['get'])
    def from_category_ids(self, request: Request) -> Response:
        pks_string = (request.query_params.get('ids', '')).strip()
        if pks_string == '':
            return Response(status=status.HTTP_400_BAD_REQUEST)
        category_getter = CategoryGetter()
        categories: Category
        pks = [int(s) for s in pks_string.split(',')]
        try:
            categories, _ = category_getter.list(pks)
        except LifeFrameException as e:
            return Response(status=e.status_code)
        mappings_dict = lf_categories_to_mappings_dict(categories)
        mappings: list[CategoryMapping] = mappings_dict.values()
        serializer = self.get_serializer(mappings, many=True)
        return Response(serializer.data)


    @action(detail=False, methods=['get'])
    def picker(self, request: Request) -> Response:
        mappings: QuerySet[CategoryMapping] = self.get_queryset() \
            .filter(show_in_picker=True) \
            .all()
        category_ids = [m.category_id for m in mappings]
        if len(category_ids) == 0:
            return Response([])

        category_getter = CategoryGetter()
        lf_category_service = LifeFrameCategoryService()
        categories, _ = category_getter.list(category_ids)
        mappings = lf_categories_to_mappings_dict(categories)
        serializer = self.get_serializer(mappings.values(), many=True)
        return Response(serializer.data)


    @action(detail=False, methods=['get'])
    def relevant(self, request: Request) -> Response:
        limit = int(request.query_params.get('limit', '10') or '10')
        try:
            category_getter = CategoryGetter()
            response = category_getter.relevant(
                life_frame_id=request.user.life_frame_id,
                limit=limit)
            mappings_dict = lf_categories_to_mappings_dict(
                response['categories'])
            mappings = mappings_dict.values()
            serializer = self.get_serializer(mappings, many=True)
            return Response(serializer.data)
        except LifeFrameUserIDRequiredError as e:
            pass
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=False, methods=['get'])
    def search(self, request: Request) -> Response:
        query_params: dict[str, str] = request.query_params

        #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=16)
        version = int(query_params.get('version', '1'))
        if version == 1:
            return self.search_v1(request)
        if version == 2:
            with MeasureTimeDiff(label='search'):
                return self.search_v2(request)
        raise Exception()
        #! END BACK COMPAT (don't need v1 after everyone updates app to version 16)

    def search_v1(self, request: Request) -> Response:
        search_phrase = (request.query_params.get('phrase', '')).strip()
        if search_phrase == '':
            return Response(status=status.HTTP_400_BAD_REQUEST)
        lf_category_service = LifeFrameCategoryService()
        lf_categories = lf_category_service.search(
            search_phrase,
            content_categories_only=True)
        mappings_dict = lf_categories_to_mappings_dict(lf_categories)
        mappings: list[CategoryMapping] = mappings_dict.values()
        mapping_serializer = self.get_serializer(mappings, many=True)
        trigram_search_annotation = TrigramSimilarity(Upper('name'), search_phrase)
        goal = 20
        custom_category_names = list(CustomCategory.objects \
            .annotate(search_similarity=trigram_search_annotation) \
            .filter(search_similarity__gt=0.1) \
            .order_by('-search_similarity') \
            [:goal] \
            .values_list('name', flat=True))
        custom_category_count = len(custom_category_names)
        if custom_category_count < goal:
            goal_remaining = goal - custom_category_count
            search_q = Q()
            words = [s for s in search_phrase.upper().split() if s != '']
            for word in words:
                search_q &= Q(name__icontains=word)
            custom_category_names += list(CustomCategory.objects \
                .filter(search_q) \
                .exclude(name__in=custom_category_names) \
                [:goal_remaining] \
                .values_list('name', flat=True))
        data = {
            'category_mappings': mapping_serializer.data,
            'custom_categories': custom_category_names,
        }

        return Response(data)

    def search_v2(self, request: Request) -> Response:
        search_phrase = (request.query_params.get('phrase', '')).strip()
        if search_phrase == '':
            return Response(status=status.HTTP_400_BAD_REQUEST)
        goal = 20
        lf_category_service = LifeFrameCategoryService()
        lf_categories = lf_category_service.search(
            search_phrase,
            content_categories_only=True)
        mappings_dict = lf_categories_to_mappings_dict(lf_categories)
        mappings: list[CategoryMapping] = mappings_dict.values()
        mapping_serializer = self.get_serializer(mappings, many=True)
        trigram_annotation = TrigramSimilarity(Upper('name'), search_phrase)
        trigram_cc_count = CustomCategory.objects.none()
        search_cc_qs = CustomCategory.objects.none()
        trigram_cc_qs = CustomCategory.objects \
            .annotate(search_similarity=trigram_annotation) \
            .filter(search_similarity__gt=0.1) \
            .order_by('-search_similarity') \
            [:goal]
        trigram_cc_count = trigram_cc_qs.count()
        if trigram_cc_count < goal:
            goal_remaining = goal - trigram_cc_count
            search_q = Q()
            words = [s for s in search_phrase.upper().split() if s != '']
            for word in words:
                search_q &= Q(name__icontains=word)
            search_cc_qs = CustomCategory.objects \
                .exclude(id__in=trigram_cc_qs) \
                .filter(search_q) \
                [:goal_remaining]
        trigram_ccs = list(trigram_cc_qs.values('id', 'name'))
        search_ccs = list(search_cc_qs.values('id', 'name'))
        data = {
            'category_mappings': mapping_serializer.data,
            'custom_categories': trigram_ccs + search_ccs,
        }
        return Response(data)


    @action(detail=False, methods=['get'])
    def content_from_category_id(self, request: Request) -> Response:
        version = request.query_params.get('version', '1').strip()

        #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
        if version == '1':
            return self._content_from_category_id_v1(request)
        elif version == '2':
            with MeasureTimeDiff(label='content_from_category_id'):
                return self._content_from_category_id_v2(request)
        #! END BACK COMPAT (don't need v1 after everyone updates app to version 15)

        msg = 'Only `version` 1 or 2 are acceptable'
        return Response(msg, status=status.HTTP_400_BAD_REQUEST)


    def _content_from_category_id_v1(self, request: Request) -> Response:
        category_id_str = (request.query_params.get('id', '')).strip()
        if category_id_str == '':
            return Response(status=status.HTTP_400_BAD_REQUEST)
        category_id = int(category_id_str)
        limit_per_type = 15
        search_phrase = request.query_params.get('search', '').strip().upper()
        continuation_key: str = request.query_params.get('continuation', '').strip()
        if continuation_key == '':
            continuation_key = uuid.uuid4()
        continuation = CategoryContentContinuation(token=continuation_key)
        items: list[Experience | Playlist] = []
        remaining_results = 0
        if search_phrase == '':
            experience_qs = CategoryContentQuerysets \
                .experiences_qs(category_id) \
                .exclude(id__in=continuation.sent_experiences) \
                .order_by('-created_at', '-id')
            remaining_results += max(experience_qs.count() - limit_per_type, 0)
            experience_qs = experience_qs[:limit_per_type]
            playlist_qs = CategoryContentQuerysets \
                .playlists_qs(category_id) \
                .exclude(id__in=continuation.sent_playlists) \
                .order_by('-created_at', '-id') \
                .distinct()
            remaining_results += max(playlist_qs.count() - limit_per_type, 0)
            playlist_qs = playlist_qs[:limit_per_type]
            experiences = [item for item in experience_qs]
            playlists = [item for item in playlist_qs]
            items = experiences + playlists
            items.sort(key=lambda x: x.created_at, reverse=True)
        else:
            trigram_search_annotation = TrigramSimilarity(Upper('name'), search_phrase)
            experience_qs = CategoryContentQuerysets \
                .experiences_qs(category_id) \
                .annotate(search_similarity=trigram_search_annotation) \
                .exclude(id__in=continuation.sent_experiences) \
                .filter(search_similarity__gt=0.1) \
                .order_by('-search_similarity')
            remaining_results += max(experience_qs.count() - limit_per_type, 0)
            experience_qs = experience_qs[:limit_per_type]
            print(str(experience_qs.query))
            playlist_qs = CategoryContentQuerysets \
                .playlists_qs(category_id) \
                .annotate(search_similarity=trigram_search_annotation) \
                .filter(search_similarity__gt=0.1) \
                .exclude(id__in=continuation.sent_playlists) \
                .order_by('-search_similarity') \
                .distinct()
            remaining_results += max(playlist_qs.count() - limit_per_type, 0)
            playlist_qs = playlist_qs[:limit_per_type]
            playlists = [item for item in playlist_qs]
            experiences = [item for item in experience_qs]
            items = experiences + playlists
            items.sort(key=lambda x: x.search_similarity, reverse=True)

        serializer_context = {
            'request': request,
        }
        results: list[dict] = []
        for item in items:
            serializer: ModelSerializer
            if type(item) is Experience:
                serializer = ExperienceViewSerializer(
                    item,
                    context=serializer_context)
                continuation.sent_experiences.append(item.id)
            elif type(item) is Playlist:
                serializer = PlaylistViewSerializer(
                    item,
                    context=serializer_context)
                continuation.sent_playlists.append(item.id)
            else:
                continue
            results.append(serializer.data)
        continuation.set_cache()
        serialized_data = {
            'continuation': continuation.token,
            'results': results,
            'remaining': remaining_results,
        }
        return Response(serialized_data)

    def _content_from_category_id_v2(self, request: Request) -> Response:
        query_params = request.query_params
        required_params = [
            'id',
            'content_type',
        ]
        allowed_params = [
            'id',
            'content_type',
            'continuation',
            'search',
            'cost',
            'stars',
            'latitude',
            'longitude',
            'radius',
        ]
        allowed_content_types = [
            'experiences',
            'users',
            'playlists',
            'all',
        ]
        for param in required_params:
            if param not in query_params:
                msg = f'"{param}" is required'
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)
            value_str: str = query_params.get(param, '').strip()
            if value_str == '':
                msg = f'"{param}" is required'
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        category_id: int = None
        content_type: str = None
        continuation_key: str = None
        search_phrase: str = None
        cost: int = None
        stars: int = None
        latitude: float = None
        longitude: float = None
        radius_miles: float = None
        filter_by_distance: bool = False
        for param in allowed_params:
            if param not in query_params:
                continue
            value_str: str = query_params.get(param)
            match (param):
                case 'id':
                    if not value_str.isdigit():
                        msg = 'id must be a number'
                        return Response(msg, status=status.HTTP_400_BAD_REQUEST)
                    category_id = int(value_str)
                case 'content_type':
                    if value_str not in allowed_content_types:
                        msg = f'content type "{content_type}" is not allowed'
                        return Response(msg, status=status.HTTP_400_BAD_REQUEST)
                    content_type = value_str.strip()
                case 'continuation':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            continuation_key = value_str
                case 'search':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            search_phrase = value_str.upper()
                case 'cost':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            cost = int(value_str)
                            if cost < 0 or cost > 4:
                                msg = f'cost must be >= 0 and <= 4'
                                return Response(msg, status=status.HTTP_400_BAD_REQUEST)
                case 'stars':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            stars = int(value_str)
                            if stars < 1 or stars > 5:
                                msg = f'stars must be >= 1 and <= 5'
                                return Response(msg, status=status.HTTP_400_BAD_REQUEST)
                case 'latitude':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            latitude = round(float(value_str), 4)
                case 'longitude':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            longitude = round(float(value_str), 4)
                case 'radius':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            radius_miles = round(float(value_str), 3)

        if latitude is not None or longitude is not None or radius_miles is not None:
            if latitude is None or longitude is None or radius_miles is None:
                msg = f'latitude, longitude, and radius are all required to filter by distance'
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)
            else:
                filter_by_distance = True

        continuation: CategoryContentContinuation = None
        if content_type != 'all':
            if continuation_key is None:
                continuation_key = uuid.uuid4()
            continuation = CategoryContentContinuation(
                token=continuation_key)

        limit_per_type = {
            'experiences': 3 if content_type == 'all' else 15,
            'playlists': 3 if content_type == 'all' else 15,
            'users': 3 if content_type == 'all' else 15,
        }

        experience_qs = Experience.objects.none()
        playlist_qs = Playlist.objects.none()
        user_qs = User.objects.none()

        match content_type:
            case 'experiences':
                experience_qs = CategoryContentQuerysets \
                    .experiences_qs(category_id)
            case 'playlists':
                playlist_qs = CategoryContentQuerysets \
                    .playlists_qs(category_id)
                if filter_by_distance:
                    experience_qs = CategoryContentQuerysets \
                        .experiences_qs(category_id)
            case 'users':
                pass
            case 'all':
                experience_qs = CategoryContentQuerysets \
                    .experiences_qs(category_id)
                playlist_qs = CategoryContentQuerysets \
                    .playlists_qs(category_id)

        experiences_order_by: list[str] = []
        playlists_order_by: list[str] = []

        # Sponsorships
        category_sponsorship = CategorySponsorship.objects \
            .filter(category_id=category_id) \
            .filter(experience_ids__len__gt=0) \
            .first()
        if category_sponsorship is not None:
            experience_qs = experience_qs.annotate(
                sponsorship_prioritized = Case(
                    When(
                        id__in=category_sponsorship.experience_ids,
                        then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()))
            experiences_order_by.append('-sponsorship_prioritized')


        # Search
        if search_phrase is None:
            experiences_order_by.append('-created_at')
            experiences_order_by.append('-id')
            playlists_order_by.append('-created_at')
            playlists_order_by.append('-id')
        else:
            trigram_search_annotation = TrigramSimilarity(
                Upper('name'),
                search_phrase)
            experience_qs = experience_qs \
                .annotate(search_similarity=trigram_search_annotation) \
                .filter(search_similarity__gt=0.1)
            playlist_qs = playlist_qs \
                .annotate(search_similarity=trigram_search_annotation) \
                .filter(search_similarity__gt=0.1)
            experiences_order_by.append('-search_similarity')
            playlists_order_by.append('-search_similarity')

        # Cost
        if cost is not None:
            filter_q = Q(average_cost_rating__lte=cost)
            filter_q &= Q(average_cost_rating__isnull=False)
            experience_qs = experience_qs \
                .filter(filter_q)
            playlist_qs = playlist_qs \
                .filter(filter_q)

        # Stars
        if stars is not None:
            filter_q = Q(average_star_rating__gte=stars)
            filter_q &= Q(average_star_rating__isnull=False)
            experience_qs = experience_qs \
                .filter(filter_q)
            playlist_qs = playlist_qs \
                .filter(filter_q)

        if filter_by_distance:
            # Note: GeoDjango documentation says Point(longitude, latitude), in that order
            # Note: srid=4326 ensures the point is stored using WGS84,
            #       the most common coordinate system for latitude and longitude.
            lat_long = Point(longitude, latitude, srid=4326)
            experience_qs = experience_qs \
                .annotate(distance_from_point=Distance('latlong__point', lat_long)) \
                .filter(distance_from_point__lte=D(mi=radius_miles))
            experiences_order_by.append('distance_from_point')
            playlist_qs = playlist_qs.filter(experiences__in=experience_qs)

        experience_qs = experience_qs \
            .order_by(*experiences_order_by) \
            .distinct()
        playlist_qs = playlist_qs \
            .order_by(*playlists_order_by) \
            .distinct()
        user_qs = user_qs \
            .distinct()

        serialized_data = {
            'continuation': continuation.token if continuation is not None else None,
            'experiences': None,
            'playlists': None,
            'users': None,
            'experience_count': experience_qs.count(),
            'playlist_count': playlist_qs.count(),
            'user_count': user_qs.count(),
        }

        if continuation is not None:
            experience_qs = experience_qs \
                .exclude(id__in=continuation.sent_experiences)
            playlist_qs = playlist_qs \
                .exclude(id__in=continuation.sent_playlists)
            user_qs = user_qs \
                .exclude(id__in=continuation.sent_users)

        experience_qs = experience_qs \
            [:limit_per_type['experiences']]
        playlist_qs = playlist_qs \
            [:limit_per_type['playlists']]
        user_qs = user_qs \
            [:limit_per_type['users']]

        serializer_context = {
            'request': request,
        }

        experience_serializer = ExperienceViewSerializer(
            experience_qs,
            many=True,
            context=serializer_context)
        playlist_serializer = PlaylistViewSerializer(
            playlist_qs,
            many=True,
            context=serializer_context)
        user_serializer = UserViewSerializer(
            user_qs,
            many=True,
            context=serializer_context)
        serialized_data['experiences'] = list(experience_serializer.data)
        serialized_data['playlists'] = list(playlist_serializer.data)
        serialized_data['users'] = list(user_serializer.data)
        if continuation is not None:
            continuation.sent_experiences += [x['id'] for x in serialized_data['experiences']]
            continuation.sent_playlists += [x['id'] for x in serialized_data['playlists']]
            continuation.sent_users += [x['id'] for x in serialized_data['users']]
            continuation.set_cache()
        return Response(serialized_data)


    @action(detail=False, methods=['get'])
    def content_from_custom_category(self, request: Request) -> Response:
        version = request.query_params.get('version', '1')
        #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
        if version == '1':
            return self._content_from_custom_category_v1(request)
        elif version == '2':
            with MeasureTimeDiff(label='content_from_custom_category'):
                response = self._content_from_custom_category_v2(request)
            return response
        #! END BACK COMPAT (don't need v1 after everyone updates app to version 15)
        msg = 'Only `version` 1 or 2 are acceptable'
        return Response(msg, status=status.HTTP_400_BAD_REQUEST)


    def _content_from_custom_category_v1(self, request: Request) -> Response:
        category_name = (request.query_params.get('name', '')).strip()
        if category_name == '':
            return Response(status=status.HTTP_400_BAD_REQUEST)
        limit_per_type = 15
        search_phrase = request.query_params.get('search', '').strip().upper()
        continuation_key: str = request.query_params.get('continuation', '').strip()
        if continuation_key == '':
            continuation_key = uuid.uuid4()
        continuation = CategoryContentContinuation(token=continuation_key)
        items: list[Experience | Playlist] = []
        remaining_results = 0
        if search_phrase == '':
            experience_qs: QuerySet[Experience] = Experience.objects \
                .filter(custom_categories__name__exact=category_name) \
                .exclude(id__in=continuation.sent_experiences) \
                .order_by('-created_at', '-id')
            remaining_results += max(experience_qs.count() - limit_per_type, 0)
            experience_qs = experience_qs[:limit_per_type]
            # Filtering by is_deleted=False is a workaround for the filter
            # not respecting the soft-delete manager (the SQL generated only
            # checks that the playlist is not deleted but not the joined experiences)
            playlist_qs: QuerySet[Playlist] = Playlist.objects \
                .filter(experiences__custom_categories__name__exact=category_name) \
                .filter(experiences__is_deleted=False) \
                .exclude(id__in=continuation.sent_playlists) \
                .order_by('-created_at', '-id') \
                .distinct()
            remaining_results += max(playlist_qs.count() - limit_per_type, 0)
            playlist_qs = playlist_qs[:limit_per_type]
            experiences = [item for item in experience_qs]
            playlists = [item for item in playlist_qs]
            items = experiences + playlists
            items.sort(key=lambda x: x.created_at, reverse=True)
        else:
            trigram_search_annotation = TrigramSimilarity(Upper('name'), search_phrase)
            experience_qs: QuerySet[Experience] = Experience.objects \
                .annotate(search_similarity=trigram_search_annotation) \
                .filter(custom_categories__name__exact=category_name) \
                .exclude(id__in=continuation.sent_experiences) \
                .filter(search_similarity__gt=0.1) \
                .order_by('-search_similarity')
            remaining_results += max(experience_qs.count() - limit_per_type, 0)
            experience_qs = experience_qs[:limit_per_type]
            # Filtering by is_deleted=False is a workaround for the filter
            # not respecting the soft-delete manager (the SQL generated only
            # checks that the playlist is not deleted but not the joined experiences)
            playlist_qs: QuerySet[Playlist] = Playlist.objects \
                .annotate(search_similarity=trigram_search_annotation) \
                .filter(experiences__custom_categories__name__exact=category_name) \
                .filter(experiences__is_deleted=False) \
                .filter(search_similarity__gt=0.1) \
                .exclude(id__in=continuation.sent_playlists) \
                .order_by('-search_similarity') \
                .distinct()
            remaining_results += max(playlist_qs.count() - limit_per_type, 0)
            playlist_qs = playlist_qs[:limit_per_type]
            playlists = [item for item in playlist_qs]
            experiences = [item for item in experience_qs]
            items = experiences + playlists
            items.sort(key=lambda x: x.search_similarity, reverse=True)

        serializer_context = {
            'request': request,
        }
        results: list[dict] = []
        for item in items:
            serializer: ModelSerializer
            if type(item) is Experience:
                serializer = ExperienceViewSerializer(
                    item,
                    context=serializer_context)
                continuation.sent_experiences.append(item.id)
            elif type(item) is Playlist:
                serializer = PlaylistViewSerializer(
                    item,
                    context=serializer_context)
                continuation.sent_playlists.append(item.id)
            else:
                continue
            results.append(serializer.data)
        continuation.set_cache()
        serialized_data = {
            'continuation': continuation.token,
            'results': results,
            'remaining': remaining_results,
        }
        return Response(serialized_data)

    def _content_from_custom_category_v2(self, request: Request) -> Response:
        # Note: Filtering playlists with `experiences__is_deleted=False`
        # is a workaround for the filter not respecting the soft-delete
        # manager (the SQL generated only checks that the playlist is not
        # deleted but not the joined experiences)

        query_params = request.query_params
        required_params = [
            'name',
            'content_type',
        ]
        allowed_params = [
            'id',
            'name',
            'content_type',
            'continuation',
            'search',
            'cost',
            'stars',
            'latitude',
            'longitude',
            'radius',
        ]
        allowed_content_types = [
            'experiences',
            'users',
            'playlists',
            'all',
        ]

        for param in required_params:
            if param not in query_params:
                msg = f'"{param}" is required'
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)
            value_str: str = query_params.get(param, '').strip()
            if value_str == '':
                msg = f'"{param}" is required'
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        cc_id: int = None
        cc_name: str = None
        content_type: str = None
        continuation_key: str = None
        search_phrase: str = None
        cost: int = None
        stars: int = None
        latitude: float = None
        longitude: float = None
        radius_miles: float = None
        filter_by_distance: bool = False
        for param in allowed_params:
            if param not in query_params:
                continue
            value_str: str = query_params.get(param)
            match (param):
                case 'id':
                    if value_str == '':
                        continue
                    if not value_str.isdigit():
                        msg = 'id must be a number'
                        return Response(msg, status=status.HTTP_400_BAD_REQUEST)
                    cc_id = int(value_str)
                case 'name':
                    cc_name = value_str.strip()
                case 'content_type':
                    if value_str not in allowed_content_types:
                        msg = f'content type "{content_type}" is not allowed'
                        return Response(msg, status=status.HTTP_400_BAD_REQUEST)
                    content_type = value_str.strip()
                case 'continuation':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            continuation_key = value_str
                case 'search':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            search_phrase = value_str.upper()
                case 'cost':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            cost = int(value_str)
                            if cost < 0 or cost > 4:
                                msg = f'cost must be >= 0 and <= 4'
                                return Response(msg, status=status.HTTP_400_BAD_REQUEST)
                case 'stars':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            stars = int(value_str)
                            if stars < 1 or stars > 5:
                                msg = f'stars must be >= 1 and <= 5'
                                return Response(msg, status=status.HTTP_400_BAD_REQUEST)
                case 'latitude':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            latitude = round(float(value_str), 4)
                case 'longitude':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            longitude = round(float(value_str), 4)
                case 'radius':
                    if value_str is not None:
                        value_str = value_str.strip()
                        if value_str != '':
                            radius_miles = round(float(value_str), 3)

        if latitude is not None or longitude is not None or radius_miles is not None:
            if latitude is None or longitude is None or radius_miles is None:
                msg = f'latitude, longitude, and radius are all required to filter by distance'
                return Response(msg, status=status.HTTP_400_BAD_REQUEST)
            else:
                filter_by_distance = True

        continuation: CategoryContentContinuation = None
        if content_type != 'all':
            if continuation_key is None:
                continuation_key = uuid.uuid4()
            continuation = CategoryContentContinuation(
                token=continuation_key)

        limit_per_type = {
            'experiences': 3 if content_type == 'all' else 15,
            'playlists': 3 if content_type == 'all' else 15,
            'users': 3 if content_type == 'all' else 15,
        }

        experience_qs = Experience.objects.none()
        playlist_qs = Playlist.objects.none()
        user_qs = User.objects.none()

        match content_type:
            case 'experiences':
                if cc_id is not None:
                    experience_qs = Experience.objects \
                        .filter(custom_categories__id__contains=cc_id)
                else:
                    experience_qs = Experience.objects \
                        .filter(custom_categories__name__exact=cc_name)
            case 'playlists':
                playlist_qs = Playlist.objects \
                    .filter(experiences__custom_categories__name__exact=cc_name) \
                    .filter(experiences__is_deleted=False)
                if filter_by_distance:
                    experience_qs = Experience.objects \
                        .filter(custom_categories__name__exact=cc_name)
            case 'users':
                pass
            case 'all':
                if cc_id is not None:
                    experience_qs = Experience.objects \
                        .filter(custom_categories__id__contains=cc_id)
                else:
                    experience_qs = Experience.objects \
                        .filter(custom_categories__name__exact=cc_name)
                playlist_qs = Playlist.objects \
                    .filter(experiences__custom_categories__name__exact=cc_name) \
                    .filter(experiences__is_deleted=False)

        experiences_order_by: list[str] = []
        playlists_order_by: list[str] = []

        # Search
        if search_phrase is None:
            experiences_order_by.append('-created_at')
            experiences_order_by.append('-id')
            playlists_order_by.append('-created_at')
            playlists_order_by.append('-id')
        else:
            trigram_search_annotation = TrigramSimilarity(
                Upper('name'),
                search_phrase)
            experience_qs = experience_qs \
                .annotate(search_similarity=trigram_search_annotation) \
                .filter(search_similarity__gt=0.1)
            playlist_qs = playlist_qs \
                .annotate(search_similarity=trigram_search_annotation) \
                .filter(search_similarity__gt=0.1)
            experiences_order_by.append('-search_similarity')
            playlists_order_by.append('-search_similarity')

        # Cost
        if cost is not None:
            filter_q = Q(average_cost_rating__lte=cost)
            filter_q &= Q(average_cost_rating__isnull=False)
            experience_qs = experience_qs \
                .filter(filter_q)
            playlist_qs = playlist_qs \
                .filter(filter_q)

        # Stars
        if stars is not None:
            filter_q = Q(average_star_rating__gte=stars)
            filter_q &= Q(average_star_rating__isnull=False)
            experience_qs = experience_qs \
                .filter(filter_q)
            playlist_qs = playlist_qs \
                .filter(filter_q)

        if filter_by_distance:
            # Note: GeoDjango documentation says Point(longitude, latitude), in that order
            # Note: srid=4326 ensures the point is stored using WGS84,
            #       the most common coordinate system for latitude and longitude.
            lat_long = Point(longitude, latitude, srid=4326)
            experience_qs = experience_qs \
                .annotate(distance_from_point=Distance('latlong__point', lat_long)) \
                .filter(distance_from_point__lte=D(mi=radius_miles))
            experiences_order_by.append('distance_from_point')
            playlist_qs = playlist_qs.filter(experiences__in=experience_qs)

        experience_qs = experience_qs \
            .order_by(*experiences_order_by) \
            .distinct()
        playlist_qs = playlist_qs \
            .order_by(*playlists_order_by) \
            .distinct()
        user_qs = user_qs \
            .distinct()

        serialized_data = {
            'continuation': continuation.token if continuation is not None else None,
            'experiences': None,
            'playlists': None,
            'users': None,
            'experience_count': experience_qs.count(),
            'playlist_count': playlist_qs.count(),
            'user_count': user_qs.count(),
        }
        if continuation is not None:
            experience_qs = experience_qs \
                .exclude(id__in=continuation.sent_experiences)
            playlist_qs = playlist_qs \
                .exclude(id__in=continuation.sent_playlists)
            user_qs = user_qs \
                .exclude(id__in=continuation.sent_users)

        experience_qs = experience_qs \
            [:limit_per_type['experiences']]
        playlist_qs = playlist_qs \
            [:limit_per_type['playlists']]
        user_qs = user_qs \
            [:limit_per_type['users']]

        serializer_context = {
            'request': request,
        }
        experience_serializer = ExperienceViewSerializer(
            experience_qs,
            many=True,
            context=serializer_context)
        playlist_serializer = PlaylistViewSerializer(
            playlist_qs,
            many=True,
            context=serializer_context)
        user_serializer = UserViewSerializer(
            user_qs,
            many=True,
            context=serializer_context)
        serialized_data['experiences'] = list(experience_serializer.data)
        serialized_data['playlists'] = list(playlist_serializer.data)
        serialized_data['users'] = list(user_serializer.data)
        if continuation is not None:
            continuation.sent_experiences += [x['id'] for x in serialized_data['experiences']]
            continuation.sent_playlists += [x['id'] for x in serialized_data['playlists']]
            continuation.sent_users += [x['id'] for x in serialized_data['users']]
            continuation.set_cache()
        return Response(serialized_data)
