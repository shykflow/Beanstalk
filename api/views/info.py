from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response


class InfoViewSet(viewsets.GenericViewSet):

    @action(detail=False, methods=['get'], authentication_classes=[], permission_classes=[])
    def earliest_supported_app_version(self, request: Request):
        version = settings.EARLIEST_SUPPORTED_APP_VERSION
        return Response(version)

    @action(detail=False, methods=['get'], authentication_classes=[], permission_classes=[])
    def facebook_login_enabled(self, request: Request):
        value = settings.FACEBOOK_LOGIN_ENABLED
        return Response(value)
