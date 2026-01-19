import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from lf_service.models import Category

from api.permissions import RequireLifeFrameWebhookAuth
from spools.models import (
    CategoryArchiveSpool,
)


class WebhookViewSet(viewsets.GenericViewSet):

    @action(
        detail=False,
        methods=['post'],
        authentication_classes=[],
        permission_classes=[RequireLifeFrameWebhookAuth])
    def category_archived(self, request: Request):
        data = request.data
        reason: int = data.get('reason')
        category_dict = data.get('category')
        if reason is None or category_dict is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        category = Category(category_dict)
        change_to: int = None
        if category.forwarded_to is not None:
            change_to = category.forwarded_to
        elif category.parent_id:
            change_to = category.parent_id
        CategoryArchiveSpool.objects.create(
            category_id=category.id,
            change_to=change_to)
        return Response()
