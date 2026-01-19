import pyotp

from django.db.models import QuerySet
from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from api.models import (
    MFAConfig,
    MFAType,
    User,
)

class Command(BaseCommand):

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--id', type=int, default=None, help="User ID")

    def handle(self, *args, **options):
        id_str = options.get('id')
        id: int
        if id_str is None:
            id_str = input('User ID: ').strip()
        try:
            id = int(id_str)
        except:
            print('Invalid id')
            exit(1)
        user = User.objects.filter(id=id).first()
        if user is None:
            print('User not found')
            exit(1)
        print()
        print(user)
        print()
        mfa_configs_qs: QuerySet[MFAConfig] = user.mfa_configs.all()
        mfa_configs = list(mfa_configs_qs)
        if len(mfa_configs) == 0:
            print('User has no MFA Configs')
            print()
            exit(0)
        print_index = 1
        for mfa_config in mfa_configs:
            mfa_type = MFAType(mfa_config.type)
            timeout: dict[str, any]
            match (mfa_type):
                case MFAType.AUTHENTICATOR:
                    timeout = settings.OTP_TIMEOUTS['authenticator']
                case MFAType.SMS:
                    timeout = settings.OTP_TIMEOUTS['sms']
                case MFAType.EMAIL:
                    timeout = settings.OTP_TIMEOUTS['email']
            totp = pyotp.TOTP(mfa_config.seed, interval=timeout['interval'])
            otp_code = totp.now()
            print(f'{print_index}:')
            print(f'    Label:    {mfa_type.label}:')
            print(f'    Code:     {otp_code}')
            print(f'    Verified: {mfa_config.verified}')
            print_index += 1
        print()
        managing = True
        while managing:
            mfa_index_str = input('Pick an MFA (number) to verify: ').strip()
            mfa_index: int
            try:
                mfa_index = int(mfa_index_str)
                mfa_index -= 1
            except:
                print('  Invalid index')
                continue
            if mfa_index >= len(mfa_configs) or mfa_index < 0:
                print('  Invalid index')
                continue
            mfa_config = mfa_configs[mfa_index]
            if mfa_config.verified:
                print('  Already verified')
                continue
            mfa_config.verified = True
            mfa_config.save()
            print('  Verified')
