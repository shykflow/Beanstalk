from django.contrib.auth import get_user_model
from rest_framework import serializers
from api.models import (
    User,
)
from api.enums import UserType

class UserLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(max_length=128)
    otp = serializers.CharField(
        max_length=6,
        min_length=6,
        required=False,
        default=None,
        allow_null=True,
        allow_blank=True)


class UserFromTokenSerializer(serializers.ModelSerializer):
    num_experiences_completed = serializers.SerializerMethodField()
    num_playlists_completed = serializers.SerializerMethodField()

    def get_num_experiences_completed(self, user: User):
        return user.completed_experiences.count()

    def get_num_playlists_completed(self, user: User):
        return user.completed_playlists.count()

    #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=16)
    #! app versions 15 and lower expect a partner boolean instead of the user_type,
    #! when app users are on app version 16+ this section can be deleted
    partner = serializers.SerializerMethodField()
    def get_partner(self, user: User):
        return user.user_type == UserType.PARTNER
    #! END BACK COMPAT

    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'partner',
            'user_type',
            'username',
            'created_at',
            'birthdate',
            'name',
            'email',
            'email_verified',
            'profile_picture',
            'profile_picture_thumbnail',
            'tagline',
            'bio',
            'website',
            'experience_visibility',
            'badge_visibility',
            'activity_push_pref',
            'like_push_pref',
            'mention_push_pref',
            'comment_push_pref',
            'follow_push_pref',
            'exp_of_the_day_push_pref',
            'accept_complete_push_pref',
            'num_experiences_completed',
            'num_playlists_completed',
        )


class UserViewSerializer(serializers.ModelSerializer):
    followed_by_viewer = serializers.BooleanField(read_only=True)
    follows_viewer = serializers.BooleanField(read_only=True)
    profile_picture = serializers.SerializerMethodField()
    profile_picture_thumbnail = serializers.SerializerMethodField()

    model = serializers.SerializerMethodField()

    def get_model(self, user: User):
        return 'User'

    #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=16)
    #! app versions 15 and lower expect a partner boolean instead of the user_type,
    #! when app users are on app version 16+ this section can be deleted
    partner = serializers.SerializerMethodField()
    def get_partner(self, user: User):
        return user.user_type == UserType.PARTNER
    #! END BACK COMPAT

    def get_profile_picture(self, user: User):
        can_show = user.is_active and bool(user.profile_picture)
        return user.profile_picture.url if can_show else None

    def get_profile_picture_thumbnail(self, user: User):
        can_show = user.is_active and bool(user.profile_picture_thumbnail)
        return user.profile_picture_thumbnail.url if can_show else None

    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'partner',
            'user_type',
            'model',
            'username',
            'created_at',
            'name',
            'profile_picture',
            'profile_picture_thumbnail',
            'email_verified',
            'tagline',
            'bio',
            'website',
            'followed_by_viewer',
            'follows_viewer',
        )


class UserSignUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            'username',
            'password',
            'email',
            'profile_picture',
        )
        extra_kwargs = {
            "profile_picture": {
                "required": False,
            },
        }


class UserEmailVerificationSerializer(serializers.Serializer):
    verification_code = serializers.CharField(min_length=8, max_length=8)


class SendVerificationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class UserEmailVerificationPasswordChangeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    verification_code = serializers.CharField(min_length=8, max_length=8)


class UserSetPasswordSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128, min_length=8)


class UserIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id',)


class UserUpdateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'birthdate',
            'name',
            'username',
            'tagline',
            'bio',
            'website',
            'activity_push_pref',
            'like_push_pref',
            'mention_push_pref',
            'comment_push_pref',
            'follow_push_pref',
            'exp_of_the_day_push_pref',
            'accept_complete_push_pref',
            'experience_visibility',
            'badge_visibility',
        )
        extra_kwargs = {
            "username": {"required": False},
        }
