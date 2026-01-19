from rest_framework import viewsets

from api.models import Comment
from api.views.filters.user_block import UserBlockFilterBackend
from api.views.mixins.comment import CommentMixin
from api.views.mixins.like import LikeMixin


class CommentViewSet(
    viewsets.GenericViewSet,
    CommentMixin,
    LikeMixin):

    queryset = Comment.objects.all()
    filter_backends = (UserBlockFilterBackend, )
