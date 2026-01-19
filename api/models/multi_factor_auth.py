import base64
from io import BytesIO
import logging
import pyotp
import qrcode
from django.conf import settings

from django.db.models import (
    BooleanField,
    CASCADE,
    CharField,
    ForeignKey,
    IntegerChoices,
    IntegerField,
    Model,
)
from django.utils.safestring import mark_safe

logger = logging.getLogger('app')

# https://github.com/pyauth/pyotp

class MFAType(IntegerChoices):
    # Don't modify these ever, they line up with what the
    # Flutter app has hard coded.
    SMS = 0
    EMAIL = 1
    AUTHENTICATOR = 2


class MFAConfig(Model):
    user = ForeignKey('User', on_delete=CASCADE, related_name='mfa_configs')
    type = IntegerField(choices=MFAType.choices)
    seed = CharField(max_length=32, unique=True, default=pyotp.random_base32)
    verified = BooleanField(default=False)

    def authenticator_provisioning_uri(self):
        issuer_name = settings.BEANSTALK_AUTHENTICATOR_LABEL
        from api.models import User
        user: User = self.user
        return pyotp.totp \
            .TOTP(self.seed) \
            .provisioning_uri(
                name=user.email,
                issuer_name=issuer_name)

    def authenticator_provisioning_uri_qr_html(self):
        if self.type != MFAType.AUTHENTICATOR:
            return mark_safe('<p>N/A</p>')
        uri = self.authenticator_provisioning_uri()
        if uri is None:
            return mark_safe('<p>Problem generating QR Code</p>')
        qr_code = qrcode.make(uri)
        buffered = BytesIO()
        qr_code.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue())
        size = 175
        return mark_safe(f"""
            <img
                src="data:image/jpg;base64, {img_base64.decode('ascii')}"
                style="width:{size}px; height:{size}px;">
        """)

    def cycle_seed(self):
        if self.type == MFAType.AUTHENTICATOR:
            logger.warning('`cycle_seed` was called on an Authenticator type.')
            return

        timeout: dict[str, any]
        match (self.type):
            case MFAType.SMS:
                timeout = settings.OTP_TIMEOUTS['sms']
            case MFAType.EMAIL:
                timeout = settings.OTP_TIMEOUTS['email']
        totp = pyotp.TOTP(self.seed, interval=timeout['interval'])
        current_code = totp.now()
        new_code: str = None
        new_seed: str = None
        while new_code is None or new_code == current_code:
            new_seed = pyotp.random_base32()
            totp = pyotp.TOTP(new_seed, interval=timeout['interval'])
            new_code = totp.now()
        self.seed = new_seed
        self.save()

    def __str__(self):
        return MFAType(self.type).label
