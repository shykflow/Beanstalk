from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.models import Interest
from api.serializers.interest import InterestSerializer

class InterestViewSet(
        viewsets.GenericViewSet,
        viewsets.mixins.RetrieveModelMixin,
        viewsets.mixins.ListModelMixin):
    serializer_class = InterestSerializer

    def get_queryset(self):
        return Interest.objects.filter(user=self.request.user)

    @action(detail=False, methods=['put'])
    def batch_update(self, request: Request) -> Response:
        validation_serializer = self.get_serializer(data=request.data, many=True)
        validation_serializer.is_valid(raise_exception=True)
        interested_category_ids = []
        for data in validation_serializer.validated_data:
            category_id = data['category']
            interested_category_ids.append(category_id)
            Interest.objects.get_or_create(user=request.user, category=category_id)
        interests = Interest.objects.filter(user=request.user).all()
        kept_interests: list[Interest] = []
        interest: Interest
        for interest in interests:
            if interest.category not in interested_category_ids:
                interest.delete()
            else:
                kept_interests.append(interest)
        serializer = self.get_serializer(kept_interests, many=True)
        return Response(serializer.data)
