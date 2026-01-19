import logging
import re

from django.conf import settings
from rest_framework.request import Request
from rest_framework.permissions import BasePermission

logger = logging.getLogger('app')

class RequireLifeFrameWebhookAuth(BasePermission):

    def has_permission(self, request: Request, view):
        lifeframe_webhook_key = settings.LIFEFRAME_WEBHOOK_KEY
        if lifeframe_webhook_key is None:
            msg = (
                'LIFEFRAME_WEBHOOK_KEY environment variable '
                'is not set, '
                'cannot recieve webhook requests from LifeFrame'
            )
            logger.error(msg)
            return False
        auth_header = request.headers.get('Authorization')
        if auth_header is None:
            return False
        # Matches a string like "Bearer asdf"
        regex_pattern_str = (
            r'^Bearer'
            r'[ ]'     # one space
            r'[^ ]+'   # 1 or more non-space characters
            r'$'
        )
        regex_pattern = re.compile(regex_pattern_str)
        match = regex_pattern.search(auth_header)
        if match is None:
            return False
        key_str = auth_header.split(' ')[1]
        if key_str != lifeframe_webhook_key:
            return False
        return super().has_permission(request, view)
