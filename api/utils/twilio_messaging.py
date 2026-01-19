from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.rest.api.v2010.account.message import MessageInstance

class TwilioMessaging:

    @staticmethod
    def _build_client() -> Client:
        account_sid = settings.TWILIO_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        return Client(account_sid, auth_token)

    @staticmethod
    def send_sms(
        to: str,
        body: str,
        force_malformed_phone_exception: bool = False)-> MessageInstance:
        from_ = settings.TWILIO_SMS_FROM_PHONE
        client = TwilioMessaging._build_client()
        if force_malformed_phone_exception:
            # This exception is a copy of a real exception that is thrown when
            # the user has an invalid phone number
            raise TwilioRestException(
                code=21211,
                details=None,
                method='POST',
                msg=f"Unable to create record: The 'To' number {to} is not a valid phone number.",
                status=400,
                uri='/Accounts/ASDF1234567890/Messages.json')
        return client.messages.create(body=body, from_=from_, to=to)
