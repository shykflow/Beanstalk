from django.forms import BooleanField
from django.db.models import BooleanField, Case, Value, When
from django.db.models.query import QuerySet
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from api.pagination import AppPageNumberPagination, get_page_size_from_request
from api.models import (
    Playlist,
    Experience,
    User,
    ExperienceCompletion,
    PlaylistCompletion,
)
from api.serializers.user import UserViewSerializer


class CompletedUsersMixin:

    @action(detail=True, methods=['get'])
    def completed_users(self, request: Request, pk) -> Response:
        instance: Playlist | Experience = self.get_object()
        qs: QuerySet
        match instance:
            case Playlist():
                qs = PlaylistCompletion.objects \
                    .filter(playlist=instance.id)
            case Experience():
                qs = ExperienceCompletion.objects \
                    .filter(experience=instance.id)
        qs = qs.order_by('-created_at') \
            .prefetch_related('user')

        page_size = get_page_size_from_request(request, 20)
        paginator = AppPageNumberPagination(page_size=page_size)
        user_completes_page = paginator.paginate_queryset(qs, request)
        user_ids = [
            user_complete.user.id
            for user_complete in user_completes_page]
        users = User.objects.filter(id__in=user_ids) \
            .annotate(followed_by_viewer = Case(
                    When(id__in=request.user.follows.all(),
                        then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()))

        user_dict = dict([(user.id, user) for user in users])
        ordered_users = [
            user_dict.get(id)
            for id in user_ids
            if id in user_dict]

        context = {
            'request': request,
        }
        return_serializer = UserViewSerializer(
            ordered_users,
            many=True,
            context=context)
        return paginator.get_paginated_response(
            return_serializer.data)
