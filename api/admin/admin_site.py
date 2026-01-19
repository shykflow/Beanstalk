from django import forms
from django.db.models import QuerySet
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.apps import AdminConfig
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from api.utils.authentication import MFAUtils, MFAResult
from api.models import (
    MFAConfig,
)

class AppLoginForm(AdminAuthenticationForm):
    authenticator = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'autocomplete': 'off',
            'maxlength': '6',
        }))

    def confirm_login_allowed(self, user) -> None:
        if settings.BEANSTALK_ADMIN_PANEL_BYPASS_AUTHENTICATOR_CHECK:
            return super().confirm_login_allowed(user)

        # TODO: Only allow Authenticator type in Admin panel login.
        # TODO: Swap below with this block of code when ready.
        # otp: str = self.cleaned_data.get('authenticator', '')
        # otp = otp.strip()
        # result, mfa_config = MFAUtils.validate_user_otp(
        #     user,
        #     otp,
        #     allowed_types=[
        #         MFAType.AUTHENTICATOR,
        #     ])
        # if result == MFAResult.AUTHENTICATED_AUTHENTICATOR:
        #     return super().confirm_login_allowed(user)
        # raise ValidationError(
        #     'OTP is invalid',
        #     code="otp")


        mfa_configs_qs: QuerySet[MFAConfig] = user.mfa_configs.all()
        mfa_configs_qs = mfa_configs_qs.filter(verified=True)
        if not mfa_configs_qs.exists():
            return super().confirm_login_allowed(user)
        otp: str = self.cleaned_data.get('authenticator', '')
        otp = otp.strip()
        result, mfa_config = MFAUtils.validate_user_otp(user, otp)
        validated = False
        match (result):
            case MFAResult.AUTHENTICATED_SMS:
                validated = True
            case MFAResult.AUTHENTICATED_EMAIL:
                validated = True
            case MFAResult.AUTHENTICATED_AUTHENTICATOR:
                validated = True
            case MFAResult.OTP_REQUIRED:
                raise ValidationError(
                    'OTP is required',
                    code="otp")
            case MFAResult.INVALID:
                raise ValidationError(
                    'OTP is invalid',
                    code="otp")
        if validated:
            mfa_config.cycle_seed()
            return super().confirm_login_allowed(user)
        raise ValidationError('Something went wrong')

class AppAdminSite(admin.AdminSite):
    site_header = "Beanstalk Admin"
    site_title = "Beanstalk Admin"
    login_form = AppLoginForm
    login_template = 'admin_login_form.html'
admin.site = AppAdminSite()
admin.autodiscover()


class AppAdminConfig(AdminConfig):
    default_site = 'api.admin.AppAdminSite'
