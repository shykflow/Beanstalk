from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.models import (
    Playlist,
    Experience,
)
from api.models.star_rating import StarRating
from api.serializers.star_rating import StarRatingSerializer


class StarRatingMixin:

    @action(detail=True, methods=['put'])
    def star_rating(self, request: Request, pk) -> Response:
        instance: Playlist | Experience = self.get_object()
        instance_type = type(instance)
        if instance_type not in (Playlist, Experience):
            raise Exception('Unsupported model type')
        star_rating_manager = instance.star_ratings.through
        kwargs = {
            'created_by': request.user,
            'playlist' if type(instance) is Playlist else 'experience': instance
        }
        star_rating: StarRating = star_rating_manager.objects.filter(**kwargs).first()
        serializer = StarRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        if star_rating is None:
            star_rating_manager.objects.create(
                rating=data['rating'],
                **kwargs)
            instance.calc_average_star_rating(set_and_save=True)
            return Response(data, status=status.HTTP_201_CREATED)
        star_rating.rating = data['rating']
        star_rating.save()
        instance.calc_average_star_rating(set_and_save=True)
        return Response(data)
