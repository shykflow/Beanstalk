import logging
import pytz
from django.utils import timezone

logger = logging.getLogger('app')

class MeasureTimeDiff(object):
    """
    If `enabled = True`, logs the time it took as
    ```
    logger.info(f"Duration: {diff} | {self.label}")
    ```
    """

    def __init__(self, label: str, enabled: bool = True, depth: int = 0):
        self.enabled = enabled
        self.label = label
        for i in range(depth):
            self.label = '- ' + label
        self.start: timezone.datetime | None = None

    def __enter__(self):
        if not self.enabled:
            return
        self.start = timezone.datetime.now(tz=pytz.timezone('UTC'))

    def __exit__(self, *args, **kwargs):
        if not self.enabled:
            return
        end = timezone.datetime.now(tz=pytz.timezone('UTC'))
        diff: timezone.timedelta = end - self.start
        logger.info(f"Duration: {diff} | {self.label}")
