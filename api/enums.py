from django.db import models

class CustomHttpStatusCodes:
    HTTP_475_MFA_REQUIRED = 475
    HTTP_476_MFA_INVALID = 476
    HTTP_485_USER_BLOCKED_YOU = 485
    HTTP_486_YOU_BLOCKED_USER = 486
    HTTP_599_LIFEFRAME_ID_MISSING = 599


class Publicity(models.IntegerChoices):
    PUBLIC = 1
    INVITE = 2
    PRIVATE = 3


class BadgePlanType(models.IntegerChoices):
    COMPLETE_TO_EARN = 1
    LIMITED_AMOUNT = 2
    LIMITED_TIME = 3


class Difficulty(models.IntegerChoices):
    EASY = 10
    MODERATE = 20
    DIFFICULT = 30
    EXTREME = 40
    # This is treated the same as a null.
    UNRATED = 100


class AttachmentType(models.IntegerChoices):
    IMAGE = 1
    VIDEO = 2
    OTHER = 3

    @staticmethod
    def from_string(attachment_type: str):
        match attachment_type.lower():
            case 'image':
                return AttachmentType.IMAGE
            case 'video':
                return AttachmentType.VIDEO
            case _:
                return AttachmentType.OTHER

class DeviceOS(models.IntegerChoices):
    IOS = 1
    ANDROID = 2
    WEB = 3
    LINUX = 4
    WINDOWS = 5
    MACOS = 6

class ReportType(models.IntegerChoices):
    # NEVER REUSE VALUES, these values can never change
    # only deprecate
    SPAM = 0
    EXPLICIT_NUDITY = 1
    DANGEROUS_ACTS = 2
    ABUSIVE_CONTENT = 3
    CHILD_ABUSE = 4
    VIOLENCE = 5
    VISUALLY_DISTURBING = 6
    DRUGS = 7
    GAMBLING = 8
    HATE_SYMBOLS = 9
    TERRORISM = 10
    FALSE_INFORMATION = 11
    OTHER = 100


class UserType(models.IntegerChoices):
    # NEVER REUSE VALUES, these values can never change only deprecate
    UNVERIFIED = 0
    VERIFIED = 1
    PARTNER = 2


class ActivityType(models.IntegerChoices):
    # NEVER REUSE VALUES, these values can never change only deprecate

    # Deprecated
    RECEIVED_MESSAGE = 0

    MENTIONED_EXPERIENCE = 100
    MENTIONED_PLAYLIST = 101
    MENTIONED_EXPERIENCE_STACK = 102
    MENTIONED_POST = 103
    MENTIONED_COMMENT = 104

    LIKED_EXPERIENCE = 200
    LIKED_PLAYLIST = 201
    LIKED_EXPERIENCE_STACK = 202
    LIKED_POST = 203
    LIKED_COMMENT = 204

    COMMENTED_EXPERIENCE = 300
    COMMENTED_PLAYLIST = 301
    COMMENTED_EXPERIENCE_STACK = 302
    COMMENTED_POST = 303
    COMMENTED_COMMENT = 304

    # Other users have accepted/completed this user's experience
    ACCEPTED_EXPERIENCE = 400
    COMPLETED_EXPERIENCE = 401
    ACCEPTED_PLAYLIST = 402
    COMPLETED_PLAYLIST = 403

    # Someone started following this users's open profile
    FOLLOW_NEW = 500
    # Someone accepted a follow request this user sent
    FOLLOW_ACCEPTED = 501
    # Someone requested to follow this user
    FOLLOW_REQUEST = 502

    # Someone added an experience to the users playlist
    ADDED_TO_YOUR_PLAYLIST = 600
    REMOVED_FROM_PLAYLIST = 601
    # Someone added an experience the user created to another playlist
    ADDED_YOUR_EXPERIENCE_TO_PLAYLIST = 602
