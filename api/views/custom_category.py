from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.models import (
    CustomCategory,
)
from api.serializers.custom_category import CustomCategoryViewSerializer

class CustomCategoryViewSet(
        viewsets.GenericViewSet,
        viewsets.mixins.RetrieveModelMixin):

    queryset = CustomCategory.objects.all()
    serializer_class = CustomCategoryViewSerializer

    @action(detail=False, methods=['get'])
    def by_name(self, request: Request) -> Response:
        query_params: dict = request.query_params
        name = query_params.get('name', '').strip()
        if name == '':
            msg = '"name" is required'
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)
        custom_category = CustomCategory.objects \
            .filter(name__exact=name) \
            .first()
        if custom_category is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CustomCategoryViewSerializer(custom_category)
        return Response(serializer.data)
