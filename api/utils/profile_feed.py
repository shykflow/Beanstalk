import json
from django.conf import settings

from api.models import User
from .continuation import Continuation


class ProfileFeedContinuation(Continuation):
    cache_timeout = 172800 # 48 hours in seconds
    def __init__(self,
            user: User,
            token: str | None):
        self.cache_key = f'profile_feed_{token}'
        self.user = user
        _data_json = self.get_cache()
        _data_dict = None
        if _data_json is not None:
            _data_dict = json.loads(_data_json)
        super().__init__(token, _data_dict)

    def debug_print(self):
        _header = '  ProfileContinuation('
        super().debug_print(_header)
