from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.models import Playlist, Experience
from api.serializers.cost_rating import CostRatingSerializer


class CostRatingMixin:

    @action(detail=True, methods=['put'])
    def cost_rating(self, request: Request, pk) -> Response:
        instance: Playlist | Experience = self.get_object()
        cost_rating_manager = instance.cost_ratings.through
        cost_rating_attributes = {
            'created_by': request.user,
            'playlist' if type(instance) is Playlist else 'experience': instance
        }
        cost_rating = cost_rating_manager.objects.filter(**cost_rating_attributes).first()
        validation_serializer = CostRatingSerializer(data=request.data)
        validation_serializer.is_valid(raise_exception=True)
        validated_data = validation_serializer.validated_data
        rating: int = validated_data['rating']
        if cost_rating is None:
            cost_rating = cost_rating_manager.objects.create(
                rating=rating,
                **cost_rating_attributes)
            instance.calc_average_cost_rating(set_and_save=True)
            serializer = CostRatingSerializer(cost_rating)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        cost_rating.rating = rating
        cost_rating.save()
        instance.calc_average_cost_rating(set_and_save=True)
        serializer = CostRatingSerializer(cost_rating)
        return Response(serializer.data)
