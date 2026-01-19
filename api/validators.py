import re

from django.db import DataError
from django.core.exceptions import ValidationError
from django.core import validators
from django.utils.translation import gettext_lazy as _
from django.utils.deconstruct import deconstructible
from django.contrib.auth import get_user_model
from rest_framework.utils.representation import smart_repr


def is_uuid4(teststr) -> bool:
    regex = r"^[0-9a-f]{8}\-[0-9a-f]{4}\-4[0-9a-f]{3}\-[89ab][0-9a-f]{3}\-[0-9a-f]{12}$"
    return re.match(regex, teststr) is not None


def qs_exists(queryset):
    try:
        return queryset.exists()
    except (TypeError, ValueError, DataError):
        return False


def qs_filter(queryset, **kwargs):
    try:
        return queryset.filter(**kwargs)
    except (TypeError, ValueError, DataError):
        return queryset.none()


def filter_queryset(self, value, queryset, field_name):
    filter_kwargs = {'%s__%s' % (field_name, 'iexact'): value}
    return qs_filter(queryset, **filter_kwargs)


def exclude_current_instance(self, queryset, instance):
    """
    If an instance is being updated, then do not include
    that instance itself as a uniqueness conflict.
    """
    if instance is not None:
        return queryset.exclude(pk=instance.pk)
    return queryset


def non_zero_validator(value):
    if value == 0:
        raise ValidationError("Must not be zero")


@deconstructible
class AvailableUsernameValidator:
    """
    Username unique case insensitive unless the user has not validated their email
    """
    message = _('Username must be unique.')

    def __call__(self, value, *args):
        queryset = get_user_model().objects.all()
        if len(args) == 0:
            # This is called from `python manage.py createsuperuser`
            queryset = queryset.filter(username__iexact=value)
        else:
            # Api endpoint call to create/update a user
            serializer_field = args[0]
            # Determine the underlying model field name. This may not be the
            # same as the serializer field name if `source=<>` is set.
            field_name = serializer_field.source_attrs[-1]
            # Determine the existing instance, if this is an update operation.
            instance = getattr(serializer_field.parent, 'instance', None)
            queryset = filter_queryset(value, queryset, field_name)
            queryset = exclude_current_instance(queryset, instance)
        if qs_exists(queryset):
            if (queryset[0].email_verified):
                raise ValidationError(self.message, code='unique')

    def __repr__(self):
        return '<%s(queryset=%s)>' % (
            self.__class__.__name__,
            smart_repr(self.queryset)
        )


@deconstructible
class AvailableEmailValidator:
    """
    Email unique case insensitive unless the user has not validated their email
    """
    message = _('Email already in use')

    def __call__(self, value, *args):
        queryset = get_user_model().objects.all()
        if len(args) == 0:
            queryset = queryset.filter(email=value)
        else:
            serializer_field = args[0]
            field_name = serializer_field.source_attrs[-1]
            instance = getattr(serializer_field.parent, 'instance', None)
            queryset = filter_queryset(value, queryset, field_name)
            queryset = exclude_current_instance(queryset, instance)
        if qs_exists(queryset):
            if (queryset[0].email_verified):
                raise ValidationError(self.message, code='unique')

    def __repr__(self):
        return '<%s(queryset=%s)>' % (
            self.__class__.__name__,
            smart_repr(self.queryset)
        )


@deconstructible
class UsernameCharacterValidator(validators.RegexValidator):
    regex = r"^[a-zA-Z0-9.+\-_]+\Z"
    message = "Username may contain only letters, numbers, and . + - _ characters."
    flags = 0


@deconstructible
class LowercaseEmailValidator(validators.RegexValidator):
    regex = r"^[^A-Z]+\Z"
    message = "Email must be lowercase."
    flags = 0


class PasswordNumberValidator():
    requirement = "Password must contain at least 1 number."
    def validate(self, password, user=None):
        if not re.findall('\d', password):
            raise ValidationError(self.requirement)
    def get_help_text(self):
        return self.requirement


class PasswordLetterCaseValidator():
    requirement = "Password must contain at least 1 uppercase and 1 lowercase letter."
    def validate(self, password, user=None):
        if not re.findall('[A-Z]', password):
            raise ValidationError(self.requirement)
        if not re.findall('[a-z]', password):
            raise ValidationError(self.requirement)
    def get_help_text(self):
        return self.requirement


class PasswordSymbolValidator():
    valid_chars = "!@#$%&*?.,;:~"
    requirement = f'Password must contain at lease one of the following: {valid_chars}"'
    def validate(self, password, user=None):
        if not re.findall('[' + self.valid_chars + ']', password):
            raise ValidationError(self.requirement)
    def get_help_text(self):
        return self.requirement

@deconstructible
class ConversationSidValidator(validators.RegexValidator):
    regex = r"^CH[a-zA-Z0-9]{32}\Z"
    message = "Not a valid Twilio Conversation SID"
    flags = 0
