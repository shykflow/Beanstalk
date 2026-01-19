import json
from django.conf import settings

from api.models import User
from .continuation import Continuation


class FollowContinuation(Continuation):
    def __init__(self, user: User, token: str | None, refresh: bool):
        self.cache_key = f'follow_feed_{token}'
        self.user = user
        _data_dict = None
        if not refresh:
            _data_json = self.get_cache()
            if _data_json is not None:
                _data_dict = json.loads(_data_json)
        super().__init__(token, _data_dict)

    def mark_seen(self):
        if not settings.SKIP_MARK_FOLLOW_FEED_SEEN:
            self.user.seen_playlists.add(*self.sent_playlists)
            self.user.seen_experiences.add(*self.sent_experiences)
            self.user.seen_posts.add(*self.sent_posts)

    def debug_print(self):
        _header = '  FollowContinuation('
        super().debug_print(_header)
