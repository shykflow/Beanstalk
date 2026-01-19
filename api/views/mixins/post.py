from django.db.models.query import QuerySet
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from api.models.experience import Experience
from api.models.playlist import Playlist
from api.pagination import AppPageNumberPagination, get_page_size_from_request
from api.models import Post
from api.serializers.post import PostViewSerializer
from api.views.post import PostViewSet

class PostMixin():

    @action(detail=True, methods=['get'])
    def posts(self, request: Request, pk) -> Response:
        instance: Playlist | Experience = self.get_object()
        posts: QuerySet[Post] = Post.objects\
            .order_by('-created_at')
        match instance:
            case Experience():
                posts = posts.filter(experience=pk)
            case Playlist():
                posts = posts.filter(playlist=pk)
            case _:
                raise Exception()

        for filter_class in PostViewSet.filter_backends:
            filter = filter_class()
            posts = filter.filter_queryset(request, posts, view=None)
        page_size = get_page_size_from_request(request, 10)
        paginator = AppPageNumberPagination(page_size=page_size)
        page = paginator.paginate_queryset(posts, request)
        context={'request': request}
        serializer = PostViewSerializer(page, many=True, context=context)
        return paginator.get_paginated_response(serializer.data)
