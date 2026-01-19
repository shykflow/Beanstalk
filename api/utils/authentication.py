from typing import Optional
import pyotp
import pytz
from django.conf import settings
from django.db.models import QuerySet
from enum import Enum

from api.models import (
    MFAConfig,
    MFAType,
    User,
)

class MFAResult(Enum):
    AUTHENTICATED_SMS = 0
    AUTHENTICATED_EMAIL = 1
    AUTHENTICATED_AUTHENTICATOR = 2
    OTP_REQUIRED = 3
    INVALID = 4


class MFAUtils:
    @staticmethod
    def validate_user_otp(
        user: User,
        otp: str,
        allowed_types: list[MFAType] = [
            MFAType.SMS,
            MFAType.EMAIL,
            MFAType.AUTHENTICATOR,
        ]) -> tuple[MFAResult, Optional[MFAConfig]]:

        otp = otp.strip()
        if otp == '':
            return MFAResult.OTP_REQUIRED, None

        mfa_configs_qs: QuerySet[MFAConfig] = user.mfa_configs.all()
        mfa_configs_qs = mfa_configs_qs.filter(type__in=allowed_types, verified=True)
        mfa_configs = list(mfa_configs_qs)

        sms_config: MFAConfig = None
        email_config: MFAConfig = None
        authenticator_config: MFAConfig = None
        for config in mfa_configs:
            match (config.type):
                case MFAType.SMS:
                    sms_config = config
                case MFAType.EMAIL:
                    email_config = config
                case MFAType.AUTHENTICATOR:
                    authenticator_config = config

        if authenticator_config is not None:
            interval = settings.OTP_TIMEOUTS['authenticator']['interval']
            totp = pyotp.TOTP(authenticator_config.seed, interval=interval)
            otp_now = totp.now()
            if otp == otp_now:
                return MFAResult.AUTHENTICATED_AUTHENTICATOR, authenticator_config

        if sms_config is not None:
            interval = settings.OTP_TIMEOUTS['sms']['interval']
            totp = pyotp.TOTP(sms_config.seed, interval=interval)
            otp_now = totp.now()
            if otp == otp_now:
                return MFAResult.AUTHENTICATED_SMS, sms_config

        if email_config is not None:
            interval = settings.OTP_TIMEOUTS['email']['interval']
            totp = pyotp.TOTP(email_config.seed, interval=interval)
            otp_now = totp.now()
            if otp == otp_now:
                return MFAResult.AUTHENTICATED_EMAIL, email_config

        return MFAResult.INVALID, None
