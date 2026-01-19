from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from api.models import AppColor

class AppColorViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = []

    def list(self, request: Request, *args, **kwargs) -> Response:
        return Response([x.color for x in AppColor.objects.all()])
