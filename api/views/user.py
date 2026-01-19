from datetime import datetime, timedelta
from uuid import uuid4
import zoneinfo
from itertools import chain
import json
import pyotp
import pytz
import logging
import sendbird_platform_sdk

from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.utils import IntegrityError
from django.http import Http404
from django.template.loader import render_to_string
from django.db.models import (
    BooleanField,
    Case,
    Count,
    F,
    Q,
    QuerySet,
    OuterRef,
    Subquery,
    Value,
    When,
)

from api.enums import ActivityType, CustomHttpStatusCodes
from api.models import (
    Activity,
    AggregateActivity,
    Playlist,
    PlaylistAccept,
    PlaylistCompletion,
    PlaylistPin,
    Experience,
    ExperienceAccept,
    ExperienceCompletion,
    MFAConfig,
    MFAType,
    Post,
    User,
    UserFollow,
    UserBlock,
)
from api.pagination import AppPageNumberPagination, get_page_size_from_request
from api.serializers.combined_content_serializer import CombinedContentSerializer
from api.services.facebook_login import FacebookLogin
from api.utils.authentication import MFAResult, MFAUtils
from api.utils.twilio_messaging import TwilioMessaging

from api.serializers.user import (
  SendVerificationEmailSerializer,
  UserEmailVerificationPasswordChangeSerializer,
  UserFromTokenSerializer,
  UserLoginSerializer,
  UserSetPasswordSerializer,
  UserSignUpSerializer,
  UserEmailVerificationSerializer,
  UserUpdateSerializer,
  UserViewSerializer,
)

from api.services.apple_login import AppleLogin
from api.services.google_login import GoogleLogin
from api.services.firebase import FirebaseService
from api.services.sendbird import Sendbird
from api.utils import random_code, split_ints
from api.utils.profile_feed import ProfileFeedContinuation
from api.views.filters.user_block import UserBlockFilterBackend
from api.views.playlist import PlaylistViewSet
from lf_service.user import LifeFrameUserService


PROFILE_FEED_SLICE_SIZE = 2

class UserViewSet(
        viewsets.GenericViewSet):

    # TODO add filter for publicity
    content_filter_backends = (
        UserBlockFilterBackend,
    )

    def get_queryset(self) -> QuerySet[User]:
        return User.objects.all()

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],)
    def user_from_token(self, request: Request, *args, **kwargs) -> Response:
        serializer = UserFromTokenSerializer(request.user)
        data = serializer.data
        data["following_count"] = request.user.follows.count()
        data["follower_count"] = UserFollow.objects.filter(followed_user=request.user).count()
        return Response(data)

    def retrieve(self, request: Request, pk, *args, **kwargs) -> Response:
        # This could be optimized
        include_relationship_data = request.query_params.get('include_relationship_data') == "true"
        include_completion_counts = request.query_params.get('include_completion_counts') == "true"
        user: User = self.get_object()
        serializer =  UserViewSerializer(user)
        data = serializer.data
        # TODO refactor to filter by blocked and less querysets
        if include_relationship_data:
            data["blocked"] = UserBlock.objects.filter(blocked_user=pk, user=request.user).exists()
            data["follows_viewer"] = UserFollow.objects.filter(followed_user=request.user.id, user=pk).exists()
            data["followed_by_viewer"] = UserFollow.objects.filter(followed_user=pk, user=request.user.id).exists()
            data["following_count"] = user.follows.count()
            data["follower_count"] = UserFollow.objects.filter(followed_user=user.id).count()
            # Users who are being followed by both the request user and retrieved users
            common_outgoing_followed_users: QuerySet = user.follows.filter(id__in=request.user.follows.all())
            data["common_outgoing_follows_count"] = common_outgoing_followed_users.count()
            # TODO: replace sampled_common_outgoing_follow_users with a paginated followers endpoints
            # Currently this is only used for the message requests page
            data["sampled_common_outgoing_follow_users"] = UserViewSerializer(common_outgoing_followed_users.order_by('?')[:2], many=True).data
            # Users who are following both the request user and retrieved users
            data["commonly_followed_by_count"] = request.user.follows_of_self.filter(user__in=user.follows_of_self.values_list('user_id', flat=True)).count()

        # TODO filter by blocked
        if include_completion_counts:
            data["num_experiences_completed"] = user.completed_experiences.count()
            data["num_playlists_completed"] = user.completed_playlists.count()

        return Response(data)

    def list(self, request: Request, *args, **kwargs) -> Response:
        user_ids = split_ints(request.query_params.get('users'))
        include_relationship_data = request.query_params.get('include_relationship_data', 'false').strip() == "true"
        users = self.get_queryset().filter(pk__in=user_ids)
        if not users.exists():
            raise Http404
        serializer = UserViewSerializer(users, many=True)
        data = serializer.data
        if include_relationship_data:
            # This could be optimized
            is_blocked_list = UserBlock.objects \
                .filter(
                    blocked_user__in=users,
                    user=request.user.id) \
                .values_list('blocked_user', flat=True)
            is_following_list = UserFollow.objects \
                .filter(
                    followed_user=request.user.id,
                    user__in=users) \
                .values_list('user', flat=True)
            follow_requesting_user = UserFollow.objects \
                .filter(
                    followed_user__in=users,
                    user=request.user.id) \
                .values_list('followed_user', flat=True)
            following_users = UserFollow.objects \
                .filter(followed_user__in=users) \
                .values('followed_user') \
                .annotate(count=Count("pk"))
            for i, user_dict in enumerate(data):
                data[i]["blocked"] = False
                data[i]["follows_viewer"] = False
                data[i]["followed_by_viewer"] = False
                data[i]["follower_count"] = 0
                if user_dict['id'] in is_blocked_list:
                    data[i]["blocked"] = True
                if user_dict['id'] in is_following_list:
                    data[i]["follows_viewer"] = True
                if user_dict['id'] in follow_requesting_user:
                    data[i]["followed_by_viewer"] = True
                for user_count in following_users:
                    if user_count['followed_user'] == user_dict['id']:
                        data[i]["follower_count"] = user_count["count"]
        return Response(data)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[],
        authentication_classes=[])
    def login(self, request: Request, *args, **kwargs) -> Response:
        # Basic validation
        serializer = UserLoginSerializer(data=request.data)
        valid = serializer.is_valid()
        if not valid:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        validated_data = serializer.validated_data
        identifier: str = validated_data.get("identifier")
        user_qs = self.get_queryset()
        if '@' in identifier:
            user_qs = user_qs.filter(email__iexact=identifier)
        else:
            user_qs = user_qs.filter(username__iexact=identifier)
        user = user_qs.first()
        if user is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        password = validated_data.get("password")
        if not user.check_password(raw_password=password):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if not user.life_frame_id:
            try:
                lifeframe_user = LifeFrameUserService().create()
                user.life_frame_id = lifeframe_user.id
                user.save()
            except:
                return Response(
                    status=CustomHttpStatusCodes.HTTP_599_LIFEFRAME_ID_MISSING)

        otp: str = validated_data.get("otp")
        mfa_response = self._generate_mfa_response(user=user, otp=otp)
        if mfa_response is not None:
            return mfa_response

        # All validation passed
        token: Token = Token.objects.filter(user_id = user.id).first()
        if not token:
            token = Token.objects.create(user=user)
        return_user_serializer = UserFromTokenSerializer(user)
        body = {'token': token.key, 'user': return_user_serializer.data}
        return Response(body)

    @action(
        detail=False,
        methods=['post'],
        authentication_classes=[],
        permission_classes=[])
    @transaction.atomic
    def apple_login(self, request: Request, *args, **kwargs):
        user, errors = AppleLogin().login_or_create(request)
        if not user:
            raise AuthenticationFailed({
                "result": "Could not authenticate",
                "errors": errors,
            })
        token, _ = Token.objects.get_or_create(user=user)

        if not user.life_frame_id:
            try:
                lifeframe_user = LifeFrameUserService().create()
                user.life_frame_id = lifeframe_user.id
                user.save()
            except:
                # This rolls back the token creation.
                transaction.rollback()
                return Response(
                    status=CustomHttpStatusCodes.HTTP_599_LIFEFRAME_ID_MISSING)
        otp = request.data.get('otp')
        mfa_response = self._generate_mfa_response(user=user, otp=otp)
        if mfa_response is not None:
            return mfa_response

        return_user_serializer = UserFromTokenSerializer(user)
        body = {'token': token.key, 'user': return_user_serializer.data}
        return Response(body)

    @action(
        detail=False,
        methods=['post'],
        authentication_classes=[],
        permission_classes=[])
    @transaction.atomic
    def google_login(self, request: Request, *args, **kwargs):
        user, errors = GoogleLogin().login_or_create(request)
        if not user:
            raise AuthenticationFailed({
                "result": "Could not authenticate",
                "errors": errors,
            })
        token, _ = Token.objects.get_or_create(user=user)

        if not user.life_frame_id:
            try:
                lifeframe_user = LifeFrameUserService().create()
                user.life_frame_id = lifeframe_user.id
                user.save()
            except:
                # This rolls back the token creation.
                transaction.rollback()
                return Response(
                    status=CustomHttpStatusCodes.HTTP_599_LIFEFRAME_ID_MISSING)
        otp = request.data.get('otp')
        mfa_response = self._generate_mfa_response(user=user, otp=otp)
        if mfa_response is not None:
            return mfa_response

        return_user_serializer = UserFromTokenSerializer(user)
        body = {'token': token.key, 'user': return_user_serializer.data}
        return Response(body)

    @action(
        detail=False,
        methods=['post'],
        authentication_classes=[],
        permission_classes=[])
    @transaction.atomic
    def facebook_login(self, request: Request, *args, **kwargs):
        # Uncomment this to re-enable blocking facebook login from environment variable.
        # Temporarily disabled while an app is submitted to Facebook.
        # if not settings.FACEBOOK_LOGIN_ENABLED:
        #     return Response(status=status.HTTP_403_FORBIDDEN)
        user, errors = FacebookLogin().login_or_create(request)
        if not user:
            raise AuthenticationFailed({
                "result": "Could not authenticate",
                "errors": errors,
            })
        token, _ = Token.objects.get_or_create(user=user)

        if not user.life_frame_id:
            try:
                lifeframe_user = LifeFrameUserService().create()
                user.life_frame_id = lifeframe_user.id
                user.save()
            except:
                # This rolls back the token creation.
                transaction.rollback()
                return Response(
                    status=CustomHttpStatusCodes.HTTP_599_LIFEFRAME_ID_MISSING)

        otp = request.data.get('otp')
        mfa_response = self._generate_mfa_response(user=user, otp=otp)
        if mfa_response is not None:
            return mfa_response

        return_user_serializer = UserFromTokenSerializer(user)
        body = {'token': token.key, 'user': return_user_serializer.data}
        return Response(body)


    @action(
        detail=False,
        methods=["post"],
        authentication_classes=[SessionAuthentication],
        permission_classes=[IsAuthenticated, IsAdminUser])
    def admin_send_verification_otp(self, request: Request, *args, **kwargs):
        """
        This endpoint is admin only and is intended to be from a button
        press in the admin.
        It allows an admin to send codes for anyone's MFA configs.
        """
        request_data = request.data
        mfa_config_id = request_data.get('id')
        if mfa_config_id is None:
            raise ValidationError()
        mfa_config = MFAConfig.objects.get(id=mfa_config_id)
        if mfa_config.verified:
            response_data = {
                'error': 'This MFA Config is already verified',
            }
            return Response(
                response_data,
                status=status.HTTP_400_BAD_REQUEST)
        user: User = mfa_config.user
        if not user.email_verified:
            response_data = {
                'error': '' + \
                    'This user is not "email verified", ' + \
                    'they are not configured correctly yet.\n\n' + \
                    'Either mark them as "email verified" or ' + \
                    'create a new user through the Flutter application.',
            }
            return Response(
                response_data,
                status=status.HTTP_400_BAD_REQUEST)
        match (mfa_config.type):
            case MFAType.AUTHENTICATOR:
                response_data = {
                    'error': 'Cannot send verification OTP for authenticator',
                }
                return Response(
                    response_data,
                    status=status.HTTP_400_BAD_REQUEST)
            case MFAType.SMS:
                mfa_config.cycle_seed()
                phone: str = user.phone
                if phone is None or phone.strip() == '':
                    response_data = {
                        'error': "User does not have a phone number set",
                    }
                    return Response(
                        response_data,
                        status=status.HTTP_400_BAD_REQUEST)
                timeout = settings.OTP_TIMEOUTS['sms']
                totp = pyotp.TOTP(mfa_config.seed, interval=timeout['interval'])
                otp_code = totp.now()
                render_context = {
                    'otp_code': otp_code,
                }
                body = render_to_string('otp_outgoing_message.txt', context=render_context)
                body = body.strip()
                try:
                    force_malformed_phone_exception: bool = request_data.get(
                        'force_malformed_phone_exception', False)
                    TwilioMessaging.send_sms(phone, body, force_malformed_phone_exception)
                    response_data = {
                        'hint': user.obfuscated_phone,
                        'timeout_label': timeout['label'],
                    }
                    return Response(
                        response_data,
                        status=status.HTTP_200_OK)
                except Exception as e:
                    response_data = {
                        'error': "Could not send to the user's phone number",
                    }
                    return Response(
                        response_data,
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            case MFAType.EMAIL:
                mfa_config.cycle_seed()
                timeout = settings.OTP_TIMEOUTS['email']
                totp = pyotp.TOTP(mfa_config.seed, interval=timeout['interval'])
                otp_code = totp.now()
                try:
                    render_context = {
                        'otp_code': otp_code,
                    }
                    email_body_text = render_to_string(
                        'otp_outgoing_message.txt',
                        context=render_context)
                    email_body_html = render_to_string(
                        'otp_outgoing_message.html',
                        context=render_context)
                    sender_domain = settings.ANYMAIL['MAILGUN_SENDER_DOMAIN']
                    email = EmailMultiAlternatives(
                        subject="Beanstalk - One time passcode",
                        body=email_body_text,
                        from_email=f"Beanstalk <no-reply@{sender_domain}>",
                        to=[user.email],
                        reply_to=[f"NoReply <no-reply@{sender_domain}>"])
                    email.attach_alternative(email_body_html, "text/html")
                    email.send()
                    response_data = {
                        'hint': user.obfuscated_email,
                        'timeout_label': timeout['label'],
                    }
                    return Response(response_data, status=status.HTTP_200_OK)
                except Exception as e:
                    response_data = {
                        'error': "Could not send to the user's email",
                    }
                    return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(
        detail=False,
        methods=["post"],
        permission_classes=[],
        authentication_classes=[])
    def request_otp(self, request: Request, *args, **kwargs) -> Response:
        """
        This endpoint is intended for users to hit during the login process.
        They will attempt to log in, a dialog will show saying they
        have MFA enabled. The standard login endpoint will have a special
        error response for when a user has MFA set up. The frontend app can
        then request to this endpoint to send either an SMS or Email to the user.

        Because this end point gives information about MFA about a user
        it requires the identifier and password. In the frontend login form
        they will have already set their username and password, so we can
        just send that information up to this endpoint.
        """
        identifier = request.data.get('identifier', '').strip()
        password = request.data.get('password', '').strip()
        method = request.data.get('method', '').strip()
        if method not in ('sms', 'email'):
            return Response(
                {'error': 'Invalid method'},
                status=status.HTTP_400_BAD_REQUEST)
        if identifier == '' or password == '' or method == '':
            return Response(
                {'error': 'identifier, password, and method are required'},
                status=status.HTTP_400_BAD_REQUEST)
        user_qs = self.get_queryset()
        if '@' in identifier:
            user_qs = user_qs.filter(email__iexact=identifier)
        else:
            user_qs = user_qs.filter(username__iexact=identifier)
        user = user_qs.first()
        if user is None:
            return Response(
                {'error': 'Invalid username / password'},
                status=status.HTTP_401_UNAUTHORIZED)
        if not user.check_password(raw_password=password):
            return Response(
                {'error': 'Invalid username / password'},
                status=status.HTTP_401_UNAUTHORIZED)

        mfa_configs: QuerySet[MFAConfig] = user.mfa_configs \
            .filter(verified=True)
        match (method):
            case 'sms':
                try:
                    mfa_config = mfa_configs.filter(type=MFAType.SMS).first()
                    if mfa_config is None:
                        return Response(
                            {'error': 'User not configured for this method'},
                            status=status.HTTP_400_BAD_REQUEST)
                    phone: str = user.phone
                    if phone is None or phone.strip() == '':
                        return Response(
                            {'error': 'Cannot send SMS, please review user\'s phone number'},
                            status=status.HTTP_400_BAD_REQUEST)
                    # Send the user a new code and invalidate any previous code
                    mfa_config.cycle_seed()
                    timeout = settings.OTP_TIMEOUTS['sms']
                    totp = pyotp.TOTP(mfa_config.seed, interval=timeout['interval'])
                    otp_code = totp.now()
                    render_context = {
                        'otp_code': otp_code,
                    }
                    sms_body = render_to_string('otp_outgoing_message.txt', context=render_context)
                    sms_body = sms_body.strip()
                    TwilioMessaging.send_sms(user.phone, sms_body)
                    response_data = {
                        'hint': user.obfuscated_phone,
                        'timeout_label': timeout['label'],
                    }
                    return Response(
                        response_data,
                        status=status.HTTP_200_OK)
                except Exception as e:
                    response_data = {
                        'error': "Could not send to the user's phone number",
                    }
                    return Response(
                        response_data,
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            case 'email':
                try:
                    mfa_config = mfa_configs.filter(type=MFAType.EMAIL).first()
                    if mfa_config is None:
                        return Response(
                            {'error': 'User not configured for this method'},
                            status=status.HTTP_400_BAD_REQUEST)
                    # Send the user a new code and invalidate any previous code
                    mfa_config.cycle_seed()
                    timeout = settings.OTP_TIMEOUTS['email']
                    totp = pyotp.TOTP(mfa_config.seed, interval=timeout['interval'])
                    otp_code = totp.now()
                    render_context = {
                        'otp_code': otp_code,
                    }
                    email_body_text = render_to_string(
                        'otp_outgoing_message.txt',
                        context=render_context)
                    email_body_html = render_to_string(
                        'otp_outgoing_message.html',
                        context=render_context)
                    sender_domain = settings.ANYMAIL['MAILGUN_SENDER_DOMAIN']
                    email = EmailMultiAlternatives(
                        subject="Beanstalk - One time passcode",
                        body=email_body_text,
                        from_email=f"Beanstalk <no-reply@{sender_domain}>",
                        to=[user.email],
                        reply_to=[f"NoReply <no-reply@{sender_domain}>"])
                    email.attach_alternative(email_body_html, "text/html")
                    email.send()
                    return Response({
                        'hint': user.obfuscated_email,
                        'timeout_label': timeout['label'],
                    })
                except Exception as e:
                    response_data = {
                        'error': "Could not send to the user's email",
                    }
                    return Response(
                        response_data,
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        response_data = {
            'error': "Something went wrong",
        }
        return Response(
            response_data,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    @action(
        detail=False,
        methods=["post"],
        permission_classes=[],
        authentication_classes=[])
    @transaction.atomic
    def sign_up(self, request: Request, *args, **kwargs) -> Response:
        # delete any user with a username that is not email verified
        existing_user = User.objects.filter(username__iexact=request.data.get('username', None), email_verified=False)
        existing_user.delete()
        serializer = UserSignUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User(username=serializer.validated_data["username"])
        password = serializer.validated_data["password"]
        try:
            validate_password(password, User)
        except ValidationError as e:
            transaction.set_rollback(True)
            errors = {'password': e.messages}
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.email = serializer.validated_data["email"]
        user.verification_code = random_code(8)
        user.code_requested_at = datetime.now(pytz.UTC)
        try:
            self._send_verification_email(user)
        except:
            transaction.set_rollback(True)
            return Response(status=status.HTTP_502_BAD_GATEWAY)
        # save before uploading user incase S3 is down or misconfigured
        profile_picture: str = serializer.validated_data.get("profile_picture")
        if profile_picture is not None:
            try:
                user.set_profile_picture(profile_picture)
            except:
                msg = "Unable to upload profile picture. Check S3 configuration"
                logging.exception(msg)
        user.save()
        token = Token.objects.create(user=user)
        body = {'token': token.key}
        return Response(body)


    @action(
        detail=True,
        methods=["DELETE"],
        permission_classes=[IsAuthenticated])
    def delete(self, request: Request, *args, **kwargs) -> Response:
        user: User = request.user
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated])
    def resend_verification_email(self, request: Request, *args, **kwargs) -> Response:
        serializer = UserFromTokenSerializer(request.user)
        user: User = self.get_queryset().filter(id=serializer.data["id"]).first()
        if user is None:
            msg = 'User not found, please login.'
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)
        if user.email_verified:
            msg = 'Email already verified.'
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)
        delta_time: timedelta = datetime.now(pytz.UTC) - user.code_requested_at
        delta_seconds = delta_time.total_seconds()
        if delta_seconds < settings.RESEND_EMAIL_TIMEOUT:
            resend_email_timeout = settings.RESEND_EMAIL_TIMEOUT - delta_seconds
            resend_email_timeout = round(resend_email_timeout)
            errors = {
                "verification_code": [f"Please wait {resend_email_timeout} seconds"],
                "resend_email_timeout": [resend_email_timeout],
            }
            return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)
        user.verification_code = random_code(8)
        user.code_requested_at = datetime.now(pytz.UTC)
        try:
            self._send_verification_email(user)
        except:
            return Response(status=status.HTTP_502_BAD_GATEWAY)
        user.save()
        return Response()

    def _send_verification_email(this, user: User) -> None:
        email_params = {
            'verification_code': user.verification_code
        }
        email_body_text = render_to_string('confirm_email.txt', context=email_params)
        email_body_html = render_to_string('confirm_email.html', context=email_params)
        sender_domain = settings.ANYMAIL['MAILGUN_SENDER_DOMAIN']
        email = EmailMultiAlternatives(
            subject="Welcome to Beanstalk!",
            body=email_body_text,
            from_email=f"Beanstalk <no-reply@{sender_domain}>",
            to=[user.email],
            reply_to=[f"NoReply <no-reply@{sender_domain}>"])
        email.attach_alternative(email_body_html, "text/html")
        email.send()

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated])
    def verify_email(self, request: Request, *args, **kwargs) -> Response:
        serializer = UserEmailVerificationSerializer(data=request.data)
        valid = serializer.is_valid()
        if not valid:
            return Response(serializer._errors, status=status.HTTP_400_BAD_REQUEST)
        validated_data: dict = serializer.validated_data
        user: User = request.user
        if not user.verification_code:
            errors = {"verification_code": ["Verification code not found."]}
            return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)
        if user.verification_code != validated_data["verification_code"]:
            errors = {"verification_code": ["Verification code does not match."]}
            return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)
        delta_time: timedelta = datetime.now(pytz.UTC) - user.code_requested_at
        if delta_time.total_seconds() > settings.EMAIL_VERIFICATION_TIMEOUT:
            errors = {"verification_code": ["Verification code expired."]}
            return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

        token_exists = Token.objects.filter(user_id = user.id).exists()
        if not token_exists:
            Token.objects.create(user=user)
        user.email_verified = True
        user.verification_code = None
        user.code_requested_at = None
        result = status.HTTP_200_OK
        if not user.life_frame_id:
            try:
                lifeframe_user = LifeFrameUserService().create()
                user.life_frame_id = lifeframe_user.id
            except:
                result = CustomHttpStatusCodes.HTTP_599_LIFEFRAME_ID_MISSING
        user.save()
        return Response(status=result)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[],
        authentication_classes=[])
    def verify_email_for_password_change(self, request: Request, *args, **kwargs) -> Response:
        serializer = UserEmailVerificationPasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data: dict = serializer.validated_data
        email: str = serializer.validated_data.get("email")
        user: User = self.get_queryset().filter(email=email).first()
        if user is None:
            return Response(
                data={"user": ['User not found.']},
                status=status.HTTP_400_BAD_REQUEST)

        if not user.verification_code:
            errors = {"verification_code": ["Verification code not found."]}
            return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)
        if user.verification_code != validated_data["verification_code"]:
            errors = {"verification_code": ["Verification code does not match."]}
            return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)
        delta_time: timedelta = datetime.now(pytz.UTC) - user.code_requested_at
        if delta_time.total_seconds() > settings.EMAIL_VERIFICATION_TIMEOUT:
            errors = {"verification_code": ["Verification code expired."]}
            return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

        token: Token = Token.objects.filter(user_id = user.id).first()
        if not token:
            token = Token.objects.create(user=user)
        user.email_verified = True
        user.verification_code = None
        user.code_requested_at = None
        user.save()
        return Response({'token': token.key})

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated])
    def change_password(self, request: Request, pk, *args, **kwargs) -> Response:
        user = request.user
        if int(pk) != user.id:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        serializer = UserSetPasswordSerializer(data=request.data)
        valid = serializer.is_valid()
        if not valid:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        validated_data: dict = serializer.validated_data
        if validated_data["email"] != user.email:
            errors = {"email": ["Not authorized"]}
            return Response(data=errors, status=status.HTTP_401_UNAUTHORIZED)
        user_email = serializer.validated_data.get("email")
        user: User = self.get_queryset().filter(email=user_email).first()
        if user is None:
            errors ={
                "user": ['No account associated with email address'],
            }
            raise Http404(errors)
        user.set_password(validated_data["password"])
        user.save()
        token = Token.objects.filter(user_id = user.id).first()
        if token:
            token.delete()
        Token.objects.create(user=user)
        return Response()

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[],
        authentication_classes=[])
    def get_password_reset_email(self, request: Request, *args, **kwargs) -> Response:
        serializer = SendVerificationEmailSerializer(data=request.data)
        valid = serializer.is_valid()
        validated_data = serializer.validated_data
        if not valid:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user: User = self.get_queryset().filter(email = validated_data["email"]).first()
        if user is None:
            return Response(
                data={"email": ['Incorrect email address.']},
                status=status.HTTP_400_BAD_REQUEST)
        # Client is requesting another email
        if user.verification_code is not None:
            delta_time: timedelta = datetime.now(pytz.UTC) - user.code_requested_at
            delta_seconds = delta_time.total_seconds()
            if delta_seconds < settings.RESEND_EMAIL_TIMEOUT:
                resend_email_timeout = round(settings.RESEND_EMAIL_TIMEOUT - delta_seconds)
                errors = {
                    "verification_code": [f"Please wait {resend_email_timeout} seconds"],
                    "resend_email_timeout": [resend_email_timeout],
                }
                return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)
        user.verification_code = random_code(8)
        user.code_requested_at = datetime.now(pytz.UTC)
        email_params = {
            'verification_code': user.verification_code
        }
        email_body_text = render_to_string(
            'reset_password_email.txt',
            context=email_params)
        email_body_html = render_to_string(
            'reset_password_email.html',
            context=email_params)
        sender_domain = settings.ANYMAIL['MAILGUN_SENDER_DOMAIN'];
        email = EmailMultiAlternatives(
            subject="Password Reset",
            body=email_body_text,
            from_email=f"Beanstalk <no-reply@{sender_domain}>",
            to=[user.email],
            reply_to=[f"NoReply <no-reply@{sender_domain}>"])
        email.attach_alternative(email_body_html, "text/html")
        try:
            email.send()
        except:
            return Response(status=status.HTTP_502_BAD_GATEWAY)
        user.save()
        return Response()

    @action(detail=False, methods=["post"])
    def set_profile_picture(self, request: Request, *args, **kwargs) -> Response:
        user: User = request.user
        profile_picture: InMemoryUploadedFile = request.FILES.get('profile_picture')
        if profile_picture is not None:
            try:
                user.set_profile_picture(profile_picture)
            except Exception:
                logging.exception("Unable to upload profile picture. Check S3 configuration")
                errors = {
                    "profile_picture": [
                        "Unable to upload profile picture. Likely network problems. Please try again later.",
                    ],
                }
                return Response(data=errors, status=status.HTTP_502_BAD_GATEWAY)
        else:
            if bool(user.profile_picture):
                user.profile_picture.delete()
            if bool(user.profile_picture_thumbnail):
                user.profile_picture_thumbnail.delete()

        user.save()
        return Response(UserViewSerializer(user).data)

    def update(self, request: Request, pk, *args, **kwargs ) -> Response:
        user: User = request.user
        data: dict = request.data
        # Do not validate the username if it hasn't changed, due to database constraints
        if user.username == data.get('username', None):
            data.pop('username')
        if user.id != int(pk):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = UserUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # validate birthday
        birthdate = validated_data['birthdate']
        now = datetime.now()
        thirteen_years_ago = datetime(
            year=now.year - 13,
            month=now.month,
            day=now.day,
            tzinfo=zoneinfo.ZoneInfo(key='UTC'))
        if birthdate > thirteen_years_ago:
            msg = {"birthdate": "Must be above the age of 13."}
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)

        for key, value in validated_data.items():
            setattr(user, key, value)
        user.save()
        response_serializer = UserFromTokenSerializer(user)
        return Response(response_serializer.data)

    @action(detail=False, methods=["get"])
    def sendbird_token(self, request: Request, *args, **kwargs) -> Response:
        # Responds with empty string if sendbird is disabled
        user: User = request.user
        using_sendbird = settings.SENDBIRD_ENABLE_MESSAGING
        sendbird = Sendbird()
        token: str
        if using_sendbird:
            try:
                response = sendbird.generate_access_token(user)
                token = response['access_token']
            except sendbird_platform_sdk.ApiException as e:
                # If the user is logging in for the first time generate_access_token fails
                if json.loads(e.body)['code'] == 400201:
                    response = sendbird.create_user(user)
                    token = response['access_token']
                # Sendbird misconfigured or down
                else:
                    token = ""
        else:
            token = ""
        return Response(token)

    @action(detail=False, methods=["get"])
    def search(self, request: Request) -> Response:
        keywords_string: str = request.query_params.get('q')
        prioritize_relevancy = request.query_params.get('prioritize_relevancy') =='true'
        ignore_self = request.query_params.get('ignore_self') =='true'

        if len(keywords_string) > 400:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        user_queryset = self.get_queryset() \
            .exclude(id__in=request.user.blocks.all()) \
            .exclude(blocks=request.user) \
            .exclude(email_verified=False) \
            .exclude(is_active=False)

        if prioritize_relevancy:
            # use activities to find the most recently relevant related users. Users dont repeat
            relevant_users = AggregateActivity.objects \
                .filter(user=request.user) \
                .exclude(related_user__in=request.user.blocks.all()) \
                .order_by('related_user','created_at') \
                .distinct('related_user')[0:30] \
                .values_list('related_user', flat=True)
            # TODO: Consider removing the Count() operation (and leave Case())
            # TODO: which would use a bool instead of an int
            user_queryset = user_queryset \
                .annotate(is_relevant=Count(Case(When(
                    id__in=relevant_users,
                    then=1)))) \
                .order_by("-is_relevant")

        if ignore_self:
            user_queryset = user_queryset.exclude(id=request.user.id)

        keywords = keywords_string.split()
        for keyword in keywords:
            user_queryset = user_queryset.filter(
                Q(username__icontains=keyword) |
                Q(first_name__icontains=keyword) |
                Q(last_name__icontains=keyword))

        users = list(user_queryset[0:30])
        serializer = UserViewSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def follow(self, request: Request, pk) -> Response:
        user: User = self.get_object()
        request_user: User = request.user
        if user.blocks.contains(request_user):
            return Response(
                status=CustomHttpStatusCodes.HTTP_485_USER_BLOCKED_YOU)
        if request_user.blocks.contains(user):
            return Response(
                status=CustomHttpStatusCodes.HTTP_486_YOU_BLOCKED_USER)
        user_follow = UserFollow()
        user_follow.user = request_user
        user_follow.followed_user = user
        try:
            # fails here if already following
            user_follow.save()
            activity = Activity(
                type=ActivityType.FOLLOW_NEW,
                user=user,
                related_user=request_user,
                is_push=user.activity_push_pref and user.follow_push_pref)
            activity.save()
        # Already following
        except IntegrityError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            fb_service = FirebaseService()
            fb_service.push_activity_to_user(activity)
        except Exception:
            logger = logging.getLogger('app')
            logger.info('Error sending new follow notification')
        return Response()

    @action(detail=True, methods=["post"])
    def unfollow(self, request: Request, pk) -> Response:
        user_follow = UserFollow.objects.filter(user=request.user, followed_user=pk).first()
        if user_follow is not None:
            user_follow.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def list_blocked(self, request: Request) -> Response:
        user: User = request.user
        users = user.blocks.all()
        serializer = UserViewSerializer(users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def block(self, request: Request, pk) -> Response:
        user: User = self.get_object()
        user_block = UserBlock()
        user_block.user = request.user
        user_block.blocked_user = user
        # remove follows bi-directionally
        follows = UserFollow.objects.filter(
            Q(user=user, followed_user=request.user) |
            Q(user=request.user, followed_user=user)) \
            .all()
        try:
            user_block.save()
            follows.delete()
            if settings.SENDBIRD_ENABLE_MESSAGING:
                sendbird = Sendbird()
                sendbird.block_user(user=request.user, blocked_user=user)
        except Exception as e:
            transaction.set_rollback(True)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response()

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def unblock(self, request: Request, pk) -> Response:
        user_block = UserBlock.objects.filter(user=request.user, blocked_user=pk).first()
        if user_block is not None:
            user: User = self.get_object()
            try:
                user_block.delete()
                if settings.SENDBIRD_ENABLE_MESSAGING:
                    sendbird = Sendbird()
                    sendbird.unblock_user(user=request.user, blocked_user=user)
            except Exception as e:
                transaction.set_rollback(True)
                return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


    @action(detail=True, methods=["get"])
    def profile_feed(self, request: Request, pk) -> Response:
        request_user: User = request.user
        profile_user: User = self.get_object()
        if profile_user.blocks.contains(request_user):
            # The UserBlockFilterBackend doesn't handle accepts / completes
            # because the user who created the content is not necessarily
            # the same as the user who accepted / completed it. This
            # guarantees users you've blocked don't get to see those.
            return Response(
                status=CustomHttpStatusCodes.HTTP_485_USER_BLOCKED_YOU)
        include_playlists = request.query_params.get('playlists') == 'true'
        include_experiences = request.query_params.get('experiences') == 'true'
        include_posts = request.query_params.get('posts') == 'true'
        # Experience/Playlist accepts and completes
        include_content_interactions = request.query_params.get('content_interactions') == 'true'
        continuation_key: str = request.query_params.get('continuation', '').strip()

        if continuation_key == '':
            continuation_key = uuid4()
        continuation = ProfileFeedContinuation(
            user=request_user,
            token=continuation_key)
        try:
            old_continuation_cache = continuation.get_cache()
            playlists_created_qs = Playlist.objects.none()
            playlists_completed_qs = Playlist.objects.none()
            playlists_accepted_qs = Playlist.objects.none()
            experiences_created_qs = Experience.objects.none()
            experiences_completed_qs = Experience.objects.none()
            experiences_accepted_qs = Experience.objects.none()
            posts_created_qs = Post.objects.none()

            if include_playlists:
                playlists_created_qs = self._playlists_created(request, profile_user)
                if include_content_interactions:
                    playlists_completed_qs = self._playlists_completed(request, profile_user)
                    # For now client doesn't want accepts to show anymore
                    # playlists_accepted_qs = self._playlists_accepted(request, profile_user)
            if include_experiences:
                experiences_created_qs = self._experiences_created(request, profile_user)
                if include_content_interactions:
                    experiences_completed_qs = self._experiences_completed(request, profile_user)
                    # For now client doesn't want accepts to show anymore
                    # experiences_accepted_qs = self._experiences_accepted(request, profile_user)
            if include_posts:
                posts_created_qs = self._posts_created(request, profile_user)

            total_to_send_counts = {
                'playlists_created': playlists_created_qs.count(),
                'playlists_accepted': playlists_accepted_qs.count(),
                'playlists_completed': playlists_completed_qs.count(),
                'experiences_created': experiences_created_qs.count(),
                'experiences_accepted': experiences_accepted_qs.count(),
                'experience_completes': experiences_completed_qs.count(),
                'posts_created': posts_created_qs.count(),
            }

            # Remove items already sent
            playlists_created_qs = playlists_created_qs \
                .exclude(id__in=continuation.sent_playlists)
            playlists_accepted_qs = playlists_accepted_qs \
                .exclude(id__in=continuation.sent_playlist_accepts)
            playlists_completed_qs = playlists_completed_qs \
                .exclude(id__in=continuation.sent_playlist_completes)
            experiences_created_qs = experiences_created_qs \
                .exclude(id__in=continuation.sent_experiences)
            experiences_accepted_qs = experiences_accepted_qs \
                .exclude(id__in=continuation.sent_experience_accepts)
            experiences_completed_qs = experiences_completed_qs \
                .exclude(id__in=continuation.sent_experience_completes)
            posts_created_qs = posts_created_qs \
                .exclude(id__in=continuation.sent_posts)

            # Set limits
            playlists_created_qs = playlists_created_qs[:PROFILE_FEED_SLICE_SIZE]
            playlists_accepted_qs = playlists_accepted_qs[:PROFILE_FEED_SLICE_SIZE]
            playlists_completed_qs = playlists_completed_qs[:PROFILE_FEED_SLICE_SIZE]
            experiences_created_qs = experiences_created_qs[:PROFILE_FEED_SLICE_SIZE]
            experiences_accepted_qs = experiences_accepted_qs[:PROFILE_FEED_SLICE_SIZE]
            experiences_completed_qs = experiences_completed_qs[:PROFILE_FEED_SLICE_SIZE]
            posts_created_qs = posts_created_qs[:PROFILE_FEED_SLICE_SIZE]

            # Record sending into the continuation
            for item in playlists_created_qs:
                continuation.sent_playlists.append(item.id)
            for item in playlists_accepted_qs:
                continuation.sent_playlist_accepts.append(item.id)
            for item in playlists_completed_qs:
                continuation.sent_playlist_completes.append(item.id)
            for item in experiences_created_qs:
                continuation.sent_experiences.append(item.id)
            for item in experiences_accepted_qs:
                continuation.sent_experience_accepts.append(item.id)
            for item in experiences_completed_qs:
                continuation.sent_experience_completes.append(item.id)
            for item in posts_created_qs:
                continuation.sent_posts.append(item.id)
            continuation.set_cache()

            total_to_send = 0
            for count in total_to_send_counts.values():
                total_to_send += count
            total_sent = 0 + \
                len(continuation.sent_playlists) + \
                len(continuation.sent_playlist_accepts) + \
                len(continuation.sent_playlist_completes) + \
                len(continuation.sent_experiences) + \
                len(continuation.sent_experience_accepts) + \
                len(continuation.sent_experience_completes) + \
                len(continuation.sent_posts)

            # Sort all feed objects into a single list

            feed_objects = list(playlists_created_qs) + \
                list(playlists_accepted_qs) + \
                list(playlists_completed_qs) + \
                list(experiences_created_qs) + \
                list(experiences_accepted_qs) + \
                list(experiences_completed_qs) + \
                list(posts_created_qs)
            feed_objects = sorted(
                feed_objects,
                reverse=True,
                key=self.get_profile_feed_object_comparison_time)

            context = {'request': request}
            return_serializer = CombinedContentSerializer(
                feed_objects,
                many=True,
                context=context)
            more_content_exists = total_sent < total_to_send
            return_data = {
                'seen_all': not more_content_exists,
                'continuation': continuation.token,
                'results': return_serializer.data}
            return Response(return_data)
        except:
            cache.set(
                key=continuation.cache_key,
                value=old_continuation_cache,
                timeout=ProfileFeedContinuation.cache_timeout)
            raise


    def _playlists_created(
        self,
        request: Request,
        user: User,
        ) -> QuerySet[Playlist]:
        qs = Playlist.objects \
            .filter(created_by=user)
        for filter_class in self.content_filter_backends:
            filter = filter_class()
            qs = filter \
                .filter_queryset(request, qs, view=None)
        qs = qs \
            .order_by('-created_at') \
            .prefetch_related('created_by', 'experiences')
        return qs


    def _playlists_accepted(
        self,
        request: Request,
        user: User,
        ) -> QuerySet[Playlist]:
        """
        Annotates the accepted_at time onto each Playlist before
        filtering with the filter backends.
        """
        sub_qs = PlaylistAccept.objects \
            .filter(playlist=OuterRef('pk')) \
            .exclude(playlist__created_by=user) \
            .filter(user=user) \
            .annotate(accepted_at=F('created_at'))
        subquery = Subquery(sub_qs.values('accepted_at')[:1])
        qs: QuerySet[Playlist] = user.accepted_playlists
        qs = qs \
            .exclude(created_by=user)\
            .annotate(accepted_at=subquery)
        for filter_class in self.content_filter_backends:
            filter = filter_class()
            qs = filter \
                .filter_queryset(request, qs, view=None)
        qs = qs.order_by('-accepted_at')
        return qs


    def _playlists_completed(
        self,
        request: Request,
        user: User,
        ) -> QuerySet[Playlist]:
        """
        Annotates the completed_at time onto each Playlist before
        filtering with the filter backends.
        """
        sub_qs = PlaylistCompletion.objects \
            .filter(playlist=OuterRef('pk')) \
            .exclude(playlist__created_by=user) \
            .filter(user=user) \
            .annotate(completed_at=F('created_at'))
        subquery = Subquery(sub_qs.values('completed_at')[:1])
        qs: QuerySet[Playlist] = user.completed_playlists
        qs = qs \
            .exclude(created_by=user)\
            .annotate(completed_at=subquery)
        for filter_class in self.content_filter_backends:
            filter = filter_class()
            qs = filter \
                .filter_queryset(request, qs, view=None)
        qs = qs.order_by('-completed_at')
        return qs


    def _experiences_created(
        self,
        request: Request,
        user: User,
        ) -> QuerySet[Experience]:
        qs = Experience.objects \
            .filter(created_by=user) \
            .prefetch_related('created_by') \
            .order_by('-created_at')
        for filter_class in self.content_filter_backends:
            filter = filter_class()
            qs = filter.filter_queryset(request, qs, view=None)
        return qs


    def _experiences_accepted(
        self,
        request: Request,
        user: User,
        ) -> QuerySet[Experience]:
        """
        Annotates the accepted_at time onto each Experience before
        filtering with the filter backends.
        """
        sub_qs = ExperienceAccept.objects \
            .filter(experience=OuterRef('pk')) \
            .exclude(experience__created_by=user) \
            .filter(user=user) \
            .annotate(accepted_at=F('created_at'))
        subquery = Subquery(sub_qs.values('accepted_at')[:1])
        qs: QuerySet[Experience] = user.accepted_experiences
        qs = qs \
            .exclude(created_by=user)\
            .annotate(accepted_at=subquery)
        for filter_class in self.content_filter_backends:
            filter = filter_class()
            qs = filter \
                .filter_queryset(request, qs, view=None)
        qs = qs.order_by('-accepted_at')
        return qs


    def _experiences_completed(
        self,
        request: Request,
        user: User,
        ) -> QuerySet[Experience]:
        """
        Annotates the completed_at time onto each Experience before
        filtering with the filter backends.
        """
        sub_qs = ExperienceCompletion.objects \
            .filter(experience=OuterRef('pk')) \
            .exclude(experience__created_by=user) \
            .filter(user=user) \
            .annotate(completed_at=F('created_at'))
        subquery = Subquery(sub_qs.values('completed_at')[:1])
        qs: QuerySet[Experience] = user.completed_experiences
        qs = qs \
            .exclude(created_by=user)\
            .annotate(completed_at=subquery)
        for filter_class in self.content_filter_backends:
            filter = filter_class()
            qs = filter \
                .filter_queryset(request, qs, view=None)
        qs = qs.order_by('-completed_at')
        return qs


    def _posts_created(
        self,
        request: Request,
        user: User,
        ) -> QuerySet[Post]:
        qs = Post.objects.filter(created_by=user) \
            .prefetch_related('created_by') \
            .order_by('-created_at')
        for filter_class in self.content_filter_backends:
            filter = filter_class()
            qs = filter.filter_queryset(request, qs, view=None)
        return qs


    def get_profile_feed_object_comparison_time(self, object):
        if hasattr(object, 'accepted_at'):
            return object.accepted_at
        if hasattr(object, 'completed_at'):
            return object.completed_at
        return object.created_at

    @action(detail=True, methods=["get"])
    def following(self, request: Request, pk) -> Response:
        # TODO test blocking
        request_user: User = request.user
        user: User = self.get_object()
        page_size = get_page_size_from_request(request, 20)
        paginator = AppPageNumberPagination(page_size=page_size)

        ordered_user_ids = UserFollow.objects\
            .filter(user=user) \
            .exclude(user__id__in=request.user.blocks.all()) \
            .exclude(user__blocks=request.user) \
            .annotate(followed_by_viewer = Case(
                    When(followed_user__in=request_user.follows.all(),
                        then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField())) \
            .order_by('-followed_by_viewer', '-created_at') \
            .prefetch_related('followed_user') \
            .values_list('followed_user', flat=True)

        users = User.objects \
            .filter(id__in=ordered_user_ids) \
            .annotate(followed_by_viewer = Case(
                    When(id__in=request_user.follows.all(),
                        then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()))

        users_dict = dict([(obj.id, obj) for obj in users])
        sorted_users = [
            users_dict.get(id)
            for id in ordered_user_ids
            if id in users_dict]

        page = paginator.paginate_queryset(sorted_users, request)
        context = {'request': request,}
        return_serializer = UserViewSerializer(page, many=True, context=context)
        return paginator.get_paginated_response(return_serializer.data)

    @action(detail=True, methods=["get"])
    def followed_by(self, request: Request, pk) -> Response:
        request_user: User = request.user
        user: User = self.get_object()
        page_size = get_page_size_from_request(request, 20)
        paginator = AppPageNumberPagination(page_size=page_size)

        ordered_user_follow_ids = UserFollow.objects\
            .filter(followed_user=user) \
            .exclude(user__id__in=request.user.blocks.all()) \
            .exclude(user__blocks=request.user) \
            .annotate(followed_by_viewer = Case(
                    When(user__id__in=request_user.follows.all(),
                        then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField())) \
            .order_by('-followed_by_viewer', '-created_at') \
            .prefetch_related('user') \
            .values_list('user', flat=True)

        following_users = User.objects \
            .filter(id__in=ordered_user_follow_ids) \
            .annotate(followed_by_viewer = Case(
                    When(id__in=request_user.follows.all(),
                        then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()))

        following_users_dict = dict([(obj.id, obj) for obj in following_users])
        sorted_users = [
            following_users_dict.get(id)
            for id in ordered_user_follow_ids
            if id in following_users_dict]

        page = paginator.paginate_queryset(sorted_users, request)
        context = {'request': request,}
        return_serializer = UserViewSerializer(page, many=True, context=context)
        return paginator.get_paginated_response(return_serializer.data)


    @action(detail=True, methods=['get'])
    def accepted_playlists(self, request: Request, pk) -> Response:
        if int(pk) != request.user.id:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        serializer_class = PlaylistViewSet.get_serializer_class(self)
        exclude_pinned = request.query_params.get('exclude_pinned') == 'true'
        qs: QuerySet[Playlist] = Playlist.objects.all()
        for filter_class in self.content_filter_backends:
            filter = filter_class()
            qs = filter.filter_queryset(request, qs, view=None)
        if exclude_pinned:
            qs = qs.exclude(users_pinned=request.user.id)
        completed_playlist_ids = PlaylistCompletion.objects \
            .filter(user=pk) \
            .values_list('playlist__id', flat=True)
        ordered_accepted_playlist_ids = PlaylistAccept.objects \
            .filter(user=pk) \
            .order_by('-created_at') \
            .values_list('playlist__id', flat=True)
        qs = qs.filter(id__in=ordered_accepted_playlist_ids) \
            .annotate(
                user_completed = Case(
                    When(id__in=completed_playlist_ids,
                    then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()),
                num_completed_experiences=Count('experiences',
                    Q(experiences__users_completed=request.user),
                    distinct=True),
                    num_experiences=Count('experiences',
                    distinct=True))
        playlists_dict = dict([(obj.id, obj) for obj in qs])
        # Sort the items based on when the accept was created
        qs = [
            playlists_dict.get(id)
            for id in ordered_accepted_playlist_ids
            if id in playlists_dict]
        # Sort the items based on when the completion was
        qs.sort(key=lambda x: x.user_completed)

        page_size = get_page_size_from_request(request, 20)
        paginator = AppPageNumberPagination(page_size=page_size)
        page = paginator.paginate_queryset(qs, request)
        serializer = serializer_class(page, many=True, context={'request': request,})
        return paginator.get_paginated_response(serializer.data)

    # Does this endpoint need to be paginated?
    @transaction.atomic
    @action(detail=True, methods=['get', 'put'])
    def pinned_playlists(self, request: Request, pk) -> Response:
        if request.method == 'GET':

            if int(pk) != request.user.id:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
            serializer_class = PlaylistViewSet.get_serializer_class(self)

            qs: QuerySet[Playlist] = Playlist.objects.all()
            for filter_class in self.content_filter_backends:
                filter = filter_class()
                qs = filter.filter_queryset(request, qs, view=None)
            qs = qs.annotate(
                    num_completed_experiences=Count('experiences',
                    Q(experiences__users_completed=request.user),
                    distinct=True),
                    num_experiences=Count('experiences',
                        distinct=True))
            ordered_pinned_playlist_ids = PlaylistPin.objects \
                .filter(user=pk) \
                .order_by('position') \
                .values_list('playlist__id', flat=True)
            qs = qs.filter(id__in=ordered_pinned_playlist_ids)

            playlists_dict = dict([(obj.id, obj) for obj in qs])
            # Sort the items based on when the pin's position
            ordered_playlists = [
                playlists_dict.get(id)
                for id in ordered_pinned_playlist_ids
                if id in playlists_dict]

            page_size = get_page_size_from_request(request, 20)
            paginator = AppPageNumberPagination(page_size=page_size)
            page = paginator.paginate_queryset(ordered_playlists, request)
            serializer = serializer_class(page, many=True, context={'request': request,})
            return paginator.get_paginated_response(serializer.data)
        else:
            data = request.data
            pins = []
            for i in range(len(data)):
                pins.append(
                    PlaylistPin(
                        playlist_id=data[i],
                        user=request.user,
                        position= i,))
            try:
                request.user.pinned_playlists.clear()
                PlaylistPin.objects.bulk_create(pins)
            except Exception as e:
                transaction.set_rollback(rollback=True)
                raise e
            return Response()

    @action(detail=True, methods=['get'])
    def completed_content(self, request: Request, pk) -> Response:
        # Get the completions and completion time.
        experience_completions = ExperienceCompletion.objects \
            .filter(user=pk) \
            .order_by('-created_at') \
            .values_list('experience__id', 'created_at')
        experience_completion_ids = [x[0] for x in experience_completions]
        experiences_qs = Experience.objects.all()
        playlist_completions = PlaylistCompletion.objects \
            .filter(user__id=pk) \
            .order_by('-created_at') \
            .values_list('playlist__id', 'created_at')
        playlist_completion_ids = [x[0] for x in playlist_completions]
        playlists = Playlist.objects.all()

        for filter_class in self.content_filter_backends:
            filter = filter_class()
            playlists = filter.filter_queryset(request, playlists, view=None)

        experiences_qs = experiences_qs.filter(id__in=experience_completion_ids)
        playlists = playlists.filter(id__in=playlist_completion_ids)

        # Sort based on when the completion was created and attach the completion time.
        experience_dict = dict([(obj.id, obj) for obj in experiences_qs])
        experiences = []
        for value in experience_completions:
            id = value[0]
            completed_at = value[1]
            experience = experience_dict.get(id)
            if experience is None:
                continue
            experience.completed_at = completed_at
            experiences.append(experience)
        playlist_dict = dict([(obj.id, obj) for obj in playlists])
        playlists = []
        for value in playlist_completions:
            id = value[0]
            completed_at = value[1]
            playlist = playlist_dict.get(id)
            if experience is None:
                continue
            playlist.completed_at = completed_at
            playlists.append(playlist)

        completed_content = sorted(
            chain(playlists, experiences),
            key=lambda objects: objects.completed_at,
            reverse=True)
        page_size = get_page_size_from_request(request, 10)
        paginator = AppPageNumberPagination(page_size=page_size)
        page = paginator.paginate_queryset(completed_content, request)
        context = {'request': request,}
        serializer = CombinedContentSerializer(page, many=True, context=context)
        return paginator.get_paginated_response(serializer.data)

    def _generate_mfa_response(self, user: User, otp: str) -> Response | None:
        # MFA validation
        mfa_configs: QuerySet[MFAConfig] = user.mfa_configs \
            .filter(verified=True)
        if mfa_configs.exists():
            if otp is None or otp.strip() == '':
                response_data = {
                    'error': 'Passcode required',
                    'mfa_types': [
                        mfa_config.type for mfa_config in mfa_configs
                    ],
                }
                return Response(
                    response_data,
                    status=CustomHttpStatusCodes.HTTP_475_MFA_REQUIRED)
            result, mfa_config = MFAUtils.validate_user_otp(user, otp)
            validated = False
            match (result):
                case MFAResult.AUTHENTICATED_SMS:
                    validated = True
                case MFAResult.AUTHENTICATED_EMAIL:
                    validated = True
                case MFAResult.AUTHENTICATED_AUTHENTICATOR:
                    validated = True
                case MFAResult.INVALID:
                    validated = False
                case MFAResult.OTP_REQUIRED:
                    response_data = {
                        'error': 'Passcode required',
                        'mfa_types': [mfa_config.type for mfa_config in mfa_configs],
                    }
                    return Response(
                        response_data,
                        status=CustomHttpStatusCodes.HTTP_475_MFA_REQUIRED)
            if not validated:
                response_data = {
                    'error': 'Invalid MFA passcode',
                    'mfa_types': [mfa_config.type for mfa_config in mfa_configs],
                }
                return Response(
                    response_data,
                    status=CustomHttpStatusCodes.HTTP_476_MFA_INVALID)
            # So the code can't be re-used within the timeframe
            if mfa_config.type in (MFAType.SMS, MFAType.EMAIL):
                mfa_config.cycle_seed()
