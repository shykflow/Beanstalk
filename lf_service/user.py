import requests

from lf_service.models import LifeFrameUser

from . import LifeFrameException, LifeFrameService

class LifeFrameUserService(LifeFrameService):

    log_label = 'LifeFrameUserService'

    def create(self) -> LifeFrameUser:
        url = ''.join([
            self.api_url,
            '/users/',
        ])
        self._log(f"POST {url}")
        response = requests.post(url, headers=self._headers())
        self._check_for_forbidden(response)
        if not (200 <= response.status_code < 300):
            raise LifeFrameException(response=response)
        data = response.json()
        return LifeFrameUser(data)
