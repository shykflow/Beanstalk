import io
import uuid
from PIL import Image
import requests

from django.conf import settings
from api.models import User
from rest_framework.request import Request
from django.core.files.base import File

from api.utils import username_from_email

import logging

logger = logging.getLogger('app')

class FacebookLogin:

    def get_app_access_token(self):
        errors = []
        app_id = settings.FACEBOOK_APP_ID
        app_secret = settings.FACEBOOK_APP_SECRET

        if app_id == '':
            errors.append('FACEBOOK_APP_ID not set.')
        if app_secret == '':
            errors.append('FACEBOOK_APP_SECRET not set')

        
        if len(errors) > 0:
            return None, errors

        # Make a server-side request to Facebook's Graph API using a secure method to handle app_secret.
        payload = {
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "client_credentials"
        }

        response = requests.post("https://graph.facebook.com/v12.0/oauth/access_token", data=payload)
        data = response.json()

        if "access_token" in data:
            app_access_token = data["access_token"]
            return app_access_token, errors
        else:
            errors.append("Failed to obtain App Access Token.")
        return None, errors

    def verify_user_token(self, app_access_token, facebook_user_token):
        errors = []
        url = 'https://graph.facebook.com/v12.0/debug_token'
        params = {
            'access_token': app_access_token,
            'input_token': facebook_user_token,
        }
        response = requests.get(url, params)
        if response.status_code != 200:
            errors.append('Error getting response from Facebook')
            return errors

        data = response.json().get('data')
        # Check to see that its a valid user token for our app.
        if data.get('app_id') != settings.FACEBOOK_APP_ID:
            errors.append("App id's don't match.")
        if data.get('type') != 'USER':
            errors.append('Type was not USER')
        return errors

    def login_or_create(self, request: Request):
        errors: list[str] = []
        facebook_user_token = request.data.get('access_token', '').strip()
        facebook_user_id = request.data.get('facebook_user_id', '').strip()
        if facebook_user_token == '':
            errors.append('Identity token not provided')
        if facebook_user_id == '':
            errors.append('Facebook user id not provided')

        if len(errors) > 0:
            return None, errors

        app_access_token, errors = self.get_app_access_token()
        if len(errors) > 0:
            return None, errors

        errors = self.verify_user_token(app_access_token, facebook_user_token)
        if len(errors) > 0:
            return None, errors
        
        # Look for an existing user
        user = User.objects.filter(facebook_user_id=facebook_user_id).first()
        if user:
            return user, errors
    
        # get user data from facebook
        url = "https://graph.facebook.com/" + facebook_user_id
        params = {
        "fields": "id,name,email,picture.width(200).height(200)",
        "access_token": facebook_user_token # User access token
        }
        facebook_response = requests.get(url, params)
        facebook_data = facebook_response.json()
        email = facebook_data.get('email')
        if email is None or email.strip() == '':
            errors.append('No email provided from Facebook')
        if len(errors) > 0:
            return None, errors

        # see if we have a user that is using the email we got from facebook
        user = User.objects.filter(email=email).first()
        if user is not None:
            if not user.email_verified:
                # Someone using this email didn't complete signup.
                # This means all associated data is unreliable.
                # A new user will be created.
                user.delete()
            else:
                # link the user
                user.facebook_user_id = facebook_user_id
                user.save()
                return user, errors

        user = User.objects.create(
            username=username_from_email(email),
            email=email,
            facebook_user_id=facebook_user_id,
            email_verified=True)

        facebook_picture_data = facebook_data.get('picture', {}).get('data')
        silhouette = facebook_picture_data.get('is_silhouette')
        if silhouette:
            return user, errors
        
        profile_picture_url = facebook_picture_data.get('url')
        try:
            max_thumb_dimension: int = settings.FILE_UPLOADS['PROFILE_PICTURE_THUMBNAIL_MAX_DIMENSION']
            filename_hash = uuid.uuid4()
            full_image_filename = f'{filename_hash}.jpg'
            thumbnail_image_filename = f'{filename_hash}-thumbnail.jpg'
            profile_picture_bytes = requests.get(profile_picture_url).content
            image_blob = io.BytesIO(profile_picture_bytes)
            image = Image.open(image_blob)
            thumbnail = image.copy()
            thumbnail_blob = io.BytesIO()
            thumbnail.thumbnail((max_thumb_dimension, max_thumb_dimension))
            thumbnail.save(thumbnail_blob, 'JPEG', optimize=True, quality=75)
            user.profile_picture.save(full_image_filename, File(image_blob))
            user.profile_picture_thumbnail.save(thumbnail_image_filename, File(thumbnail_blob))
        except Exception as e:
            logger.error(str(e))
            user.profile_picture.delete()
            user.profile_picture_thumbnail.delete()
            raise
        return user, errors
            