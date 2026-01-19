
import colorama
from urllib.parse import urlencode
import logging
import os
import requests

logger = logging.getLogger('app')

class LifeFrameUserIDRequiredError(Exception):
    pass

class LifeFrameException(Exception):
    def __init__(
        self,
        response: requests.Response=None,
        message="Something went wrong querying LifeFrame"):
        self.response: requests.Response | None = response
        self.status_code: int | None = None
        if response is not None:
            self.status_code = response.status_code
        message = f'{message}\nStatus Code: {self.status_code}, {message}'
        super().__init__(message)

class LifeFrameService:

    log_label = 'LifeFrameService'

    def __init__(self):
        env = os.environ
        self.api_url = env.get('LIFEFRAME_API_URL')
        self.public_key = env.get('LIFEFRAME_PUBLIC_KEY')
        self.secret_key = env.get('LIFEFRAME_SECRET_KEY')

    def _log(self, message: str):
        color = colorama.Fore.CYAN
        bright = colorama.Style.BRIGHT
        reset = colorama.Style.RESET_ALL
        logger.info(f"{bright}{color}{self.log_label}:{reset} {message}")

    def _headers(self, secret=True):
        return {
            'Authorization': f'Api-Key {self.secret_key if secret else self.public_key}',
        }

    def params_to_url_part(self, params: dict[str, str]) -> str:
        if not bool(params):
            return ''
        return '?' + urlencode(params)

    def _check_for_forbidden(self, response: requests.Response):
        if response.status_code == 403:
            raise Exception("""
                403 Forbidden
                Could not create LifeFrame user.

                Does Beanstalk have valid API keys?

                To generate the default development API keys, open the LifeFrame
                project and give this Django command:

                python manage.py create_org_with_keys --name "Beanstalk" --prebuilt

            """)
