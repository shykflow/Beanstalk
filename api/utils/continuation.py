import json
import logging

from django.core.cache import cache

logger = logging.getLogger('app')

class Continuation:
    """
    This class should not be instantiated directly and will not work properly
    without a subclass setting `self.cache_key` and calling `super().__init__`.

    Example usage:

    ```
    class MyContinuation(Continuation):
        def __init__(self, token, *args, **kwargs):
            self.cache_key = f'my_prefix_{token}'
            _data_json = self.get_cache()
            _data_dict = None if _data_json is None else json.loads(_data_json)
            super().__init__(token, _data_dict)

        def debug_print(self):
            header = 'my_header'
            super().debug_print(header)
    ```
    """
    cache_timeout = 3600 # One hour in seconds

    def __init__(self, token: str | None, data_dict: dict | None):
        self.token = token
        self.sent_experiences: list[int]
        self.sent_playlists: list[int]
        self.sent_playlist_accepts: list[int]
        self.sent_playlist_completes: list[int]
        self.sent_experience_accepts: list[int]
        self.sent_experience_completes: list[int]
        self.sent_posts: list[int]
        if data_dict is not None:
            self.sent_experiences = data_dict.get('sent_experiences', [])
            self.sent_playlists = data_dict.get('sent_playlists', [])
            self.sent_playlist_accepts = data_dict.get('sent_playlist_accepts', [])
            self.sent_playlist_completes = data_dict.get('sent_playlist_completes', [])
            self.sent_experience_accepts = data_dict.get('sent_experience_accepts', [])
            self.sent_experience_completes = data_dict.get('sent_experience_completes', [])
            self.sent_posts = data_dict.get('sent_posts', [])
        else:
            self.refresh_cache()

    def get_cache(self):
        return cache.get(self.cache_key)

    def set_cache(self,  data_dict: dict = {}):
        data_dict['sent_experiences'] = getattr(self, 'sent_experiences', [])
        data_dict['sent_playlists'] = getattr(self, 'sent_playlists', [])
        data_dict['sent_playlist_accepts'] = getattr(self, 'sent_playlist_accepts', [])
        data_dict['sent_playlist_completes'] = getattr(self, 'sent_playlist_completes', [])
        data_dict['sent_experience_accepts'] = getattr(self, 'sent_experience_accepts', [])
        data_dict['sent_experience_completes'] = getattr(self, 'sent_experience_completes', [])
        data_dict['sent_posts'] = getattr(self, 'sent_posts', [])
        data_json = json.dumps(data_dict)
        cache.set(
            key=self.cache_key,
            value=data_json,
            timeout=self.cache_timeout
        )

    def refresh_cache(self):
        self.sent_experiences = []
        self.sent_playlists = []
        self.sent_playlist_accepts = []
        self.sent_playlist_completes = []
        self.sent_experience_accepts = []
        self.sent_experience_completes = []
        self.sent_posts = []
        self.set_cache()

    def debug_print(self, header: str, additional_lines: list[str] = []):
        output_strings = [
            header,
            f'    cache_key: {self.cache_key},',
            f'    cache_timeout: {self.cache_timeout},',
            f'    sent_experiences: [{", ".join(map(str, self.sent_experiences))}]',
            f'    sent_playlists: [{", ".join(map(str, self.sent_playlists))}]',
            f'    sent_playlist_accepts: [{", ".join(map(str, self.sent_playlist_accepts))}]',
            f'    sent_playlist_completes: [{", ".join(map(str, self.sent_playlist_completes))}]',
            f'    sent_experience_accepts: [{", ".join(map(str, self.sent_experience_accepts))}]',
            f'    sent_experience_completes: [{", ".join(map(str, self.sent_experience_completes))}]',
            f'    sent_posts: [{", ".join(map(str, self.sent_posts))}]',
        ]

        for line in additional_lines:
            output_strings.append(line)
        output_strings.append('  )')
        logger.info('\n'.join(output_strings))
