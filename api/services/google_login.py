import requests

from authlib.jose import JWTClaims

from django.utils import timezone
from rest_framework.request import Request

from api.models import (
    User,
)
from api.utils import username_from_email

class GoogleLogin:

    def decode_token(self, id_token: str) -> JWTClaims | None:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
        response = requests.get(url)
        return response.json()

    def authenticate_token(self, id_token, token_user):
        errors = []
        token = self.decode_token(id_token)
        if not token:
            errors.append('Invalid token')
            return None, errors
        
        iss = token.get('iss', None) #issuer
        aud = token.get('aud', None) #audience
        sub = token.get('sub', None) #subject
        exp:int = token.get('exp', None) #expiration time
        expiration_date = None
        if exp:
            exp = int(exp)
            expiration_date = timezone.datetime.fromtimestamp(exp, tz=timezone.utc)

        expired = not expiration_date or expiration_date < timezone.now()
        unexpected_iss = not iss or iss != 'https://accounts.google.com'
        valid_auds = [
            # Web client ID
            '713287916464-84jdc9dvolts1hmqoc44ugoggbl4su6c.apps.googleusercontent.com',
            # iOS client ID
            '713287916464-9ej4mb1h8k4j9ko87ksj499ekfjbqicg.apps.googleusercontent.com'
        ]
        unexpected_aud = not aud or aud not in valid_auds
        users_match = sub and sub == token_user
        if expired or unexpected_iss or unexpected_aud or not users_match:
            errors.append('Invalid token')

        email = token.get('email', None)
        if not email:
            raise errors.append('Email must be provided to create a new account')

        email_verified_value = token.get('email_verified', None)
        email_verified = email_verified_value and email_verified_value == 'true'
        if not email_verified:
            raise errors.append('Email must be verified through apple')

        return token, errors

    def login_or_create(self, request: Request):
        errors: list[str] = []
        id_token: str|None = request.data.get('id_token')
        if id_token is None or id_token.strip() == '':
            errors.append('Identity token not provided')
        google_user_id = request.data.get('google_user_id')
        if google_user_id is None or google_user_id.strip() == '':
            errors.append('Google user id not provided')

        if len(errors) > 0:
            return None, errors

        token_data, err = self.authenticate_token(id_token, google_user_id)
        errors += err
        if len(errors) > 0:
            return None, errors
        
        user = User.objects.filter(google_user_id=google_user_id).first()
        if user is not None:
            return user, errors

        email: str = token_data.get('email', '').strip()
        if email == '':
            errors.append('Bad email')
            return None, errors

        user = User.objects.filter(email=email).first()
        if user is not None:
            if not user.email_verified:
                # Someone using this email didn't complete signup.
                # This means all associated data is unreliable.
                # A new user will be created.
                user.delete()
            else:
                # This case is when the user sign up on android
                # and is now using the apple sign in.
                user.google_user_id = google_user_id
                user.save()
                return user, errors

        # Create a new user
        try:
            user = User.objects.create(
                username=username_from_email(email),
                email=email,
                google_user_id=google_user_id,
                email_verified=True)
            return user, errors
        except:
            errors.append('Failed during user creation')
            return None, errors
