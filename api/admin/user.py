import pyotp
from django.forms import ValidationError, ModelForm, CharField
from django.forms.models import BaseInlineFormSet
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.http import HttpRequest
from django_admin_inline_paginator.admin import TabularInlinePaginated
from django.utils.safestring import SafeText
from django.urls import reverse

from api.admin.abstract.soft_delete_model_admin import (
    SoftDeleteTabularInlinePaginated,
)
from api.admin.admin_site import AppAdminSite
from api.admin.report import ReportInline
from api.models import (
    Device,
    Experience,
    Interest,
    MFAConfig,
    MFAType,
    Playlist,
    Post,
    Showcase,
    User,
)

class UserReportInline(ReportInline):
    # Setting the fk_name because reports have two users on them
    # (created_by and offender)
    fk_name = 'offender'
    fields = ReportInline.fields + (
        'experience',
        'playlist',
        'post',
        'comment',
    )


class MFAConfigForm(ModelForm):
    verify_otp = CharField(required=False,
        help_text='This MFA is not usable until verified')


class MFAConfigFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        # Gather some info without hitting the database
        non_delete_forms = []
        num_creating = 0
        verify_forms = []
        for form in self.forms:
            if form.instance.id is None:
                num_creating += 1
            if form.cleaned_data['verify_otp'].strip() != '':
                verify_forms.append(form)
            data = form.cleaned_data
            if data['DELETE'] != True:
                non_delete_forms.append(form)
            if not form.is_valid():
                # Form will already have errors in it shown to
                # the user, no sense doing anything complex.
                return
        if num_creating > 1:
            raise ValidationError(
                'Cannot create more than 1 OTP Config at a time')

        # Check for duplicate types
        sms_form = None
        email_form = None
        authenticator_form = None
        for form in non_delete_forms:
            data = form.cleaned_data
            match (data['type']):
                case MFAType.SMS:
                    if sms_form is not None:
                        form.add_error(
                            'type',
                            'Cannot have multiple SMS types')
                    sms_form = form
                case MFAType.EMAIL:
                    if email_form is not None:
                        form.add_error(
                            'type',
                            'Cannot have multiple Email types')
                    email_form = form
                case MFAType.AUTHENTICATOR:
                    if authenticator_form is not None:
                        form.add_error(
                            'type',
                            'Cannot have multiple Authenticator types')
                    authenticator_form = form

        for form in verify_forms:
            verify_otp = form.cleaned_data['verify_otp']
            mfa_config: MFAConfig = form.instance
            if mfa_config.verified:
                form.add_error('verify_otp', 'Already verified')
                continue
            timeout: dict[str, any]
            match (mfa_config.type):
                case MFAType.SMS:
                    timeout = settings.OTP_TIMEOUTS['sms']
                case MFAType.EMAIL:
                    timeout = settings.OTP_TIMEOUTS['email']
                case MFAType.AUTHENTICATOR:
                    timeout = settings.OTP_TIMEOUTS['authenticator']
            totp = pyotp.TOTP(mfa_config.seed, interval=timeout['interval'])
            otp_code = totp.now()
            if otp_code != verify_otp:
                form.add_error('verify_otp', 'Code did not match, try repeating the process')
                continue
            mfa_config.verified = True
            mfa_config.save()



class MFAConfigInline(admin.TabularInline):
    class Media:
        js = (
            'js/admin_inline_send_verify_otp.js',
        )
    verbose_name = 'MFA Config'
    verbose_name_plural = 'MFA Configs - Only make ONE at a time!'
    form = MFAConfigForm
    formset = MFAConfigFormSet
    model = MFAConfig
    max_num = 3
    extra = 0
    # classes = ['collapse']
    fields = (
        'type',
        'seed',
        'qr_code',
        'send_verify_button',
        'verify_otp',
        'verified',
    )
    readonly_fields = (
        'seed',
        'qr_code',
        'verified',
        'send_verify_button',
    )

    def send_verify_button(self, mfa_config: MFAConfig):
        if mfa_config.type == MFAType.AUTHENTICATOR:
            return SafeText('<p>N/A</p>')
        if mfa_config.verified:
            return SafeText('<p>Already verified</p>')
        html = f"""
            <style>
                .send-verify-button {{
                    border-radius: 5px;
                    color: white;
                    background-color: #91b11b;
                    padding: 8px;
                    cursor: pointer;
                }}
                .send-verify-button.sending {{
                    background-color: grey;
                    cursor: wait;
                }}
            </style>
            <button
                type="button"
                id="send-verify-button-{mfa_config.id}"
                class="send-verify-button"
                onclick="send_verification_otp({mfa_config.id}); return false;">
                Send Verification
            </button>
        """
        return SafeText(html)

    def qr_code(self, config: MFAConfig):
        html = config \
            .authenticator_provisioning_uri_qr_html()
        return html


class InterestInline(TabularInlinePaginated):
    model = Interest
    per_page = 20
    extra = 0
    classes = ['collapse']


class ShowcaseInline(admin.TabularInline):
    model = Showcase
    extra = 0
    classes = ['collapse']


class UserBlockedInline(TabularInlinePaginated):
    model = User.blocks.through
    per_page = 20
    extra = 0
    fk_name = 'user'
    raw_id_fields = ('blocked_user',)
    verbose_name_plural = "Blocking"
    classes = ['collapse']


class UserBlockingMeInline(TabularInlinePaginated):
    model = User.blocks.through
    per_page = 20
    extra = 0
    fk_name = 'blocked_user'
    raw_id_fields = ('user',)
    verbose_name_plural = "Blocking me"
    classes = ['collapse']


class UserFollowsInline(TabularInlinePaginated):
    model = User.follows.through
    per_page = 20
    extra = 0
    fk_name = 'user'
    raw_id_fields = ('followed_user',)
    verbose_name_plural = "Follows"
    classes = ['collapse']


class UserFollowingMeInline(TabularInlinePaginated):
    model = User.follows.through
    per_page = 20
    extra = 0
    fk_name = 'followed_user'
    raw_id_fields = ('user',)
    verbose_name_plural = "Following me"
    classes = ['collapse']


class UserAcceptedExperienceInline(SoftDeleteTabularInlinePaginated):
    model = User.accepted_experiences.through
    per_page = 20
    extra = 0
    fk_name = 'user'
    fields = ('experience',)
    raw_id_fields = ('experience',)
    verbose_name_plural = "Accepted Experiences"
    classes = ['collapse']


class UserCompletedExperienceInline(SoftDeleteTabularInlinePaginated):
    model = User.completed_experiences.through
    per_page = 20
    extra = 0
    fk_name = 'user'
    fields = ('experience',)
    raw_id_fields = ('experience',)
    verbose_name_plural = "Completed Experiences"
    classes = ['collapse']


class UserAcceptedPlaylistsInline(SoftDeleteTabularInlinePaginated):
    model = User.accepted_playlists.through
    per_page = 20
    extra = 0
    fk_name = 'user'
    fields = ('playlist',)
    raw_id_fields = ('playlist',)
    verbose_name_plural = "Accepted Playlists"
    classes = ['collapse']


class UserCompletedPlaylistsInline(SoftDeleteTabularInlinePaginated):
    model = User.completed_playlists.through
    per_page = 20
    extra = 0
    fk_name = 'user'
    fields = ('playlist',)
    raw_id_fields = ('playlist',)
    verbose_name_plural = "Completed Playlists"
    classes = ['collapse']


class UserSavedPlaylistsInline(SoftDeleteTabularInlinePaginated):
    model = User.saved_playlists.through
    per_page = 20
    extra = 0
    fk_name = 'user'
    fields = ('playlist',)
    raw_id_fields = ('playlist',)
    verbose_name_plural = "Saved Playlists"
    classes = ['collapse']


class UserPinnedPlaylistsInline(SoftDeleteTabularInlinePaginated):
    model = User.pinned_playlists.through
    per_page = 20
    extra = 0
    fk_name = 'user'
    fields = ('playlist', 'position',)
    raw_id_fields = ('playlist',)
    verbose_name_plural = "Pinned Playlists"
    classes = ['collapse']


class UserSavedExperiencesInline(SoftDeleteTabularInlinePaginated):
    model = User.saved_experiences.through
    per_page = 20
    extra = 0
    fk_name = 'user'
    fields = ('experience',)
    raw_id_fields = ('experience',)
    verbose_name_plural = "Saved Experiences"
    classes = ['collapse']


class _CreatedByInline(SoftDeleteTabularInlinePaginated):
    per_page = 20
    extra = 0
    fields = ('_name', 'created_at',)
    readonly_fields = ('_name', 'created_at',)
    classes = ['collapse']

    def _name(self, instance: Experience | Playlist | Post):
        info = (instance._meta.app_label, instance._meta.model_name)
        admin_url = reverse('admin:%s_%s_change' % info, args=(instance.pk,))
        return SafeText(f'''
            <a href="{admin_url}">
                {instance.name}
            </a>''')


class UserCreatedExperiencesInline(_CreatedByInline):
    model = Experience
    verbose_name_plural = "Created Experiences"


class UserCreatedPlaylistsInline(_CreatedByInline):
    model = Playlist
    verbose_name_plural = "Created Playlists"


class UserCreatedPostsInline(_CreatedByInline):
    model = Post
    verbose_name_plural = "Created Posts"


class UserAdmin(DjangoUserAdmin):
    list_display = (
        'username',
        'email',
        'user_type',
        'is_staff',
        'is_superuser',
        'email_verified',
        'created_at',
        'last_used_device',
    )
    search_fields = (
        'username',
        'email',
        'name',
        'first_name',
        'last_name',
        'phone',
    )
    inlines = (
        MFAConfigInline,
        InterestInline,
        ShowcaseInline,
        UserBlockedInline,
        UserBlockingMeInline,
        UserFollowsInline,
        UserFollowingMeInline,
        UserAcceptedExperienceInline,
        UserCompletedExperienceInline,
        UserAcceptedPlaylistsInline,
        UserCompletedPlaylistsInline,
        UserSavedPlaylistsInline,
        UserPinnedPlaylistsInline,
        UserSavedExperiencesInline,
        UserCreatedExperiencesInline,
        UserCreatedPlaylistsInline,
        UserCreatedPostsInline,
        UserReportInline,
    )
    fieldsets = (
        (
            'Personal',
            {
                'fields': (
                    'user_type',
                    'username',
                    'profile_picture',
                    'profile_picture_thumbnail',
                    'name',
                    'phone',
                    'birthdate',
                    'first_name',
                    'last_name',
                    'email',
                    'password',
                    'tagline',
                    'bio',
                    'website',
                ),
            }
        ),
        (
            'Authorization',
            {
                'fields': (
                    'life_frame_id',
                    'apple_user_id',
                    'google_user_id',
                    'facebook_user_id',
                ),
            }
        ),
        (
            'Signup Process',
            {
                'fields': (
                    'email_verified',
                    'verification_code',
                    'code_requested_at',
                ),
            }
        ),
        (
            'Settings',
            {
                'fields': (
                    'experience_visibility',
                    'badge_visibility',
                    'activity_push_pref',
                    'like_push_pref',
                    'mention_push_pref',
                    'comment_push_pref',
                    'follow_push_pref',
                    'accept_complete_push_pref',
                    'exp_of_the_day_push_pref',
                ),
            }
        ),
        (
            'Administration',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'notify_about_new_content_reports',
                    # 'is_superuser',
                    'groups',
                    'user_permissions',
                    'last_login',
                    'date_joined',
                ),
            }
        ),
    )

    def get_readonly_fields(self, request: HttpRequest, viewed_user: User):
        readonly_fields = [
            'last_used_device',
            'apple_user_id',
            'google_user_id',
            'facebook_user_id',
        ]
        perms = request.user.get_all_permissions()
        if 'api.change_user_email_verified' not in perms:
            readonly_fields.append('email_verified')
        if 'api.can_manage_user_permissions' not in perms:
            readonly_fields.append('user_permissions')
        return readonly_fields

    def last_used_device(self, u: User) -> str:
        most_recent_device = Device.objects \
            .filter(user=u) \
            .order_by('-last_check_in') \
            .first()
        if most_recent_device is not None:
            d = most_recent_device.details
            return f'{d["brand"]} - {d["model"]} - {d["app_version"]}'
        return None

    # override to set profile picture thumbnail
    def save_model(self, request, obj, form, change):
        user: User = obj
        if 'profile_picture' in request.FILES.keys():
            user.set_profile_picture(request.FILES['profile_picture'])
        super().save_model(request, obj, form, change)

admin.site.register(User, UserAdmin, site=AppAdminSite)
