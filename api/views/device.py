import pytz
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.models import Device

class DevicesViewSet(viewsets.ViewSet):

    @action(
        detail=False,
        methods=['post'],
        # Bypassing the `IsVerifiedPermission` permission class because the user does not need to
        # verify their email before giving us their device token.
        permission_classes=[IsAuthenticated])
    def update_fcm_token(self, request: Request) -> Response:
        request_data = request.data
        token: str = request_data.get('token')
        if token is None or token != str(token) or token.strip() == '':
            return Response('"token" is required', status=status.HTTP_400_BAD_REQUEST)
        device, created = Device.objects.get_or_create(
            user=request.user,
            token=token)
        time_zone = pytz.timezone("UTC")
        if not created:
            device.last_check_in = timezone.datetime.now(tz=time_zone)
            device.save()
        try:
            details = request_data.get('details', {})
            device.details = details
            device.minutes_offset = request_data.get('minutes_offset')
            device.os = request_data.get('os')
            device.save()
        except:
            pass
        return Response()
