from datetime import timedelta
import threading
import time
from typing import MutableMapping

from emoji import EmojiInfo

debounce: MutableMapping[EmojiInfo, float] = {}
debounce_lock = threading.Lock()


def seen_too_recently(emoji: EmojiInfo, debounce_interval: timedelta) -> bool:
    with debounce_lock:
        now = time.time()

        last_used = debounce.get(emoji)
        debounce_interval_ago = now - debounce_interval.total_seconds()

        debounce[emoji] = now  # Update the last seen time to ~now

        if last_used is None or last_used < debounce_interval_ago:
            return False

        return True
