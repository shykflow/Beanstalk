import requests

from . import LifeFrameService



class LifeFrameUtilService(LifeFrameService):

    log_label = 'LifeFrameUtilService'

    def healthcheck(self) -> requests.Response:
        url = ''.join([
            self.api_url,
            '/healthcheck/',
        ])
        self._log(f"GET {url}")
        return requests.get(url)

    def check_api_key(self) -> requests.Response:
        url = ''.join([
            self.api_url,
            '/check_api_key/',
        ])
        self._log(f"GET {url}")
        response = requests.get(url, headers=self._headers())
        self._check_for_forbidden(response)
        return response
