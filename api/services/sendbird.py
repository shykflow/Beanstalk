from django.conf import settings
import json
import logging
import requests

import sendbird_platform_sdk
from sendbird_platform_sdk import ApiClient, Configuration
from sendbird_platform_sdk.api import user_api, group_channel_api
from sendbird_platform_sdk.model import (
    create_user_data,
    update_user_by_id_data,
    gc_create_channel_data,
    gc_invite_as_members_data,
)


from api.models import (
    User,
    UserBlock,
)

logger = logging.getLogger('app')

class Sendbird:
    using_sendbird = settings.SENDBIRD_ENABLE_MESSAGING

    def create_clients(self):
        '''Must be called at the start of any method that uses Sendbird.
        This allows Sendbird unit testing using the test environment'''
        self.api_token = settings.SENDBIRD_API_TOKEN
        application_id = settings.SENDBIRD_APPLICATION_ID

        self.client: ApiClient
        if (self.using_sendbird):
            configuration = Configuration(
                host=f"https://api-{application_id}.sendbird.com")
            client = ApiClient(configuration=configuration)
            self.user_client = user_api.UserApi(client)
            self.channel_client = group_channel_api.GroupChannelApi(client)


    def create_user(self, user: User):
        if not self.using_sendbird:
            return
        self.create_clients()
        userData = create_user_data.CreateUserData(
            user_id=str(user.id),
            nickname=user.username,
            profile_url=str(user.id),
            issue_access_token=True,
            metadata={})
        response = self.user_client.create_user(
            self.api_token,
            create_user_data=userData)
        # sendbird will have thrown an error if the user
        # already existed by this point
        blocks = UserBlock.objects.filter(blocked_user=user).all()
        for block in blocks:
            self.block_user(
                user=block.user,
                blocked_user=block.blocked_user)
        return response

    def generate_access_token(self, user: User):
        if not self.using_sendbird:
            return
        self.create_clients()
        update_user_data = update_user_by_id_data.UpdateUserByIdData(
            user_id=str(user.id),
            nickname=user.username,
            profile_url='',
            issue_access_token=True)
        return self.user_client.update_user_by_id(self.api_token, str(user.id), update_user_by_id_data=update_user_data)

    def register_device(self, user, device):
        if not self.using_sendbird:
            return
        self.create_clients()
        # TODO fix this
        token_type = "token_type_example" # str |
        add_registration_or_device_token_data = \
            add_registration_or_device_token_data.AddRegistrationOrDeviceTokenData(
                gcm_reg_token="gcm_reg_token_example",
                huawei_device_token = "",
                apns_device_token="")

        push_cred_sid = self.android_notifications_sid
        # TODO implement IOS notifs
        #   if Device.isIOS:
        #     push_cred_sid = self.ios_push_credential_sid

        #  TODO ensure user notif prefs
        try:
            return self.user_client.add_registration_or_device_token(
                self.api_token,
                str(user.id),
                token_type,
                add_registration_or_device_token_data=add_registration_or_device_token_data)
        except sendbird_platform_sdk.ApiException as e:
            print("Exception when calling UserApi->add_registration_or_device_token: %s\n" % e)
        return ""

    def create_channel(self,
            requesting_user: User,
            invited_users: list[User],
            joined_users: list[User],
            is_group_chat: bool):
        if not self.using_sendbird:
            return
        self.create_clients()
        channel_name = ''
        ids = []

        for user in invited_users + joined_users + [requesting_user]:
            id_str = str(user.id)
            ids.append(id_str)
            channel_name += " " + user.username
            # users must exist for a distinct channel to be created or invited
            try:
                self.create_user(user)
            except sendbird_platform_sdk.ApiException as e:
                # Sendbird user already exists
                if json.loads(e.body)['code'] != 400202:
                    raise e
        # remove leading space
        channel_name = channel_name.strip()

        invitation_status = {}
        for user in invited_users:
            invitation_status[str(user.id)] = "invited_by_non_friend"
        for user in joined_users:
            invitation_status[str(user.id)] = "joined"
        invitation_status[str(requesting_user.id)] = "joined"

        custom_type= "group-message" if is_group_chat else "direct-message"
        create_channel_data = gc_create_channel_data.GcCreateChannelData(
            ids,
            name=channel_name,
            # TODO make group and dm custom types
            custom_type=custom_type,
            is_distinct= not is_group_chat,
            invitation_status=invitation_status)
        # _check_return_type bypasses type checks on the response. It bypasses a bug with the API library
        response = self.channel_client.gc_create_channel(
            self.api_token,
            gc_create_channel_data=create_channel_data,
            _check_return_type=False)

        return response.channel_url

    def delete_channel(self, channel_url: str):
        '''For unit test cleanup, use archive for anything else'''
        if not self.using_sendbird:
            return
        self.create_clients()
        # _check_return_type bypasses type checks on the response. It bypasses a bug with the API library
        return self.channel_client.gc_delete_channel_by_url(
            self.api_token,
            channel_url,
            _check_return_type=False)

    def get_channel(self, channel_url: str):
        self.create_clients()
        return self.channel_client.gc_view_channel_by_url(
            self.api_token,
            channel_url=channel_url)

    def get_all_channels(self):
        '''For unit test cleanup'''
        self.create_clients()
        return self.channel_client.gc_list_channels(
            self.api_token,
            _check_return_type=False)

    def add_participant(self, channel_url: str, users: list[User]):
        if not self.using_sendbird:
            return
        self.create_clients()
        userIds = []
        for user in users:
            userIds.append(str(user.id))
            try:
                self.create_user(user)
            except sendbird_platform_sdk.ApiException as e:
                # Sendbird user already exists
                if json.loads(e.body)['code'] != 400202:
                    raise e
        data = gc_invite_as_members_data.GcInviteAsMembersData(
            channel_url=channel_url,
            user_ids=userIds,
            users=[],
            invitation_status={},
            hidden_status={},
        )
        self.channel_client.gc_invite_as_members(
            self.api_token,
            channel_url=channel_url,
            gc_invite_as_members_data=data,
            _check_return_type=False)

    def block_user(self, user: User, blocked_user: User):
        if not self.using_sendbird:
            return
        body = {
            'user_id': str(user.id),
            'target_id': str(blocked_user.id),
        }
        url = ''.join([
            'https://api-',
            settings.SENDBIRD_APPLICATION_ID,
            '.sendbird.com/v3/users/',
            str(user.id),
            '/block',
        ])
        headers = {
            "Api-Token": settings.SENDBIRD_API_TOKEN
        }
        response = requests.post(url, json=body, headers=headers)
        if response.status_code != 200:
            response_body = json.loads(response.text)
            if response.status_code == 400 \
                and response_body['code'] == 400201:
                msg = 'Failed to block on Sendbird\'s side because user was not found, ' + \
                    'they have not participated in any conversations yet or ' + \
                    'Sendbird failed to create their user.'
                logger.info(msg)
                return
            raise Exception(response=response)

    def unblock_user(self, user: User, blocked_user: User):
        if not self.using_sendbird:
            return
        url = ''.join([
            'https://api-',
            settings.SENDBIRD_APPLICATION_ID,
            '.sendbird.com/v3/users/',
            str(user.id),
            '/block/',
            str(blocked_user.id),
        ])
        headers = {
            "Api-Token": settings.SENDBIRD_API_TOKEN
        }
        response = requests.delete(url, headers=headers)
        if response.status_code != 200:
            response_body = json.loads(response.text)
            if response.status_code == 400 \
                and response_body['code'] == 400201:
                msg = 'Failed to unblock on Sendbird\'s side because user was not found, ' + \
                    'they have not participated in any conversations yet or ' + \
                    'Sendbird failed to create their user.'
                logger.info(msg)
                return
            raise Exception(response=response)
