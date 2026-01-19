from django.core.cache import cache
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.services.google_maps import GoogleMapsService
from api.utils.earth import EarthHelper
from api.validators import is_uuid4

class GoogleMapsViewSet(viewsets.ViewSet):
    cache_timeout = 172800 # 48 hours in seconds
    service = GoogleMapsService()

    @action(detail=False, methods=['get'])
    def autocompleteplace(self, request: Request) -> Response:
        search_term = request.query_params.get('search_term', '').strip()
        if len(search_term) == 0:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        token = request.query_params.get('token')
        if token is None or not is_uuid4(token):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        data = self.service.autocomplete_place(search_term, token)
        return Response(data)

    @action(detail=False, methods=['get'])
    def placedetails(self, request: Request) -> Response:
        place_id = request.query_params.get('place_id')
        if place_id is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        token = request.query_params.get('token')
        if token is None or not is_uuid4(token):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        cache_key = f'place_details_{place_id}'
        cached_details = cache.get(cache_key)
        if cached_details is not None:
            return Response(cached_details)
        data = self.service.place_details(place_id, token)
        cache.set(
            key=cache_key,
            value=data,
            timeout=self.cache_timeout)
        return Response(data)

    @action(detail=False, methods=['get'])
    def reversegeocode(self, request: Request) -> Response:
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        if latitude is None or longitude is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            latfloat = float(latitude)
            lngfloat = float(longitude)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if not EarthHelper.valid_coordinates(latfloat, lngfloat):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        latlng = f'{latitude},{longitude}'
        data = self.service.reverse_geocode(latlng)
        return Response(data)
