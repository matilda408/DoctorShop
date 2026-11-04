import time
from datetime import datetime

from src.core.constants import TIMEZONE

START_TIME: int = int(time.time())


def datetime_now() -> datetime:
    return datetime.now(tz=TIMEZONE)


def get_uptime() -> int:
    uptime_seconds = int(time.time() - START_TIME)
    return uptime_seconds
