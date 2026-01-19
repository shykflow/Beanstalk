import requests

from authlib.jose import JsonWebKey, jwt, JWTClaims

from django.utils import timezone
from rest_framework.request import Request

from api.models import (
    User,
)
from api.utils import username_from_email

class AppleLogin:
    auth_public_keys = []

    def get_auth_public_key(self):
        if self.auth_public_keys:
            return self.auth_public_keys
        else:
            url = "https://appleid.apple.com/auth/keys"
            response = requests.get(url)
            auth_public_keys = response.json().get('keys')
            return auth_public_keys


    def decode_token(self, token:str) -> JWTClaims | None:
        decoded_token = None
        keys = self.get_auth_public_key()
        for k in keys:
            key = JsonWebKey.import_key(k)
            try:
                decoded_token = jwt.decode(token, key)
                break
            except:
                continue
        return decoded_token


    def authenticate_token(self, token, token_user):
        errors = []
        token = self.decode_token(token)
        if not token:
            errors.append('Invalid token')
            return None, errors

        iss = token.get('iss', None) #issuer
        aud = token.get('aud', None) #audience
        sub = token.get('sub', None) #subject
        exp = token.get('exp', None) #expiration time
        expiration_date = None
        if exp:
            expiration_date = timezone.datetime.fromtimestamp(exp, tz=timezone.utc)

        expired = not expiration_date or expiration_date < timezone.now()
        unexpected_iss = not iss or iss != 'https://appleid.apple.com'
        unexpected_aud = not aud or aud != 'com.beanstalk.beanstalk'
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
        token: str|None = request.data.get('identity_token')
        if token is None or token.strip() == '':
            errors.append('Identity token not provided')
        apple_user_id = request.data.get('apple_user_id')
        if apple_user_id is None or apple_user_id.strip() == '':
            errors.append('Apple user id not provided')

        if len(errors) > 0:
            return None, errors
        token_data, err = self.authenticate_token(token, apple_user_id)
        errors += err
        if len(errors) > 0:
            return None, errors
        user = User.objects.filter(apple_user_id=apple_user_id).first()
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
                user.apple_user_id = apple_user_id
                user.save()
                return user, errors

        # Create a new user
        try:
            user = User.objects.create(
                username=username_from_email(email),
                email=email,
                apple_user_id=apple_user_id,
                email_verified=True)
            return user, errors
        except:
            errors.append('Failed during user creation')
            return None, errors
