from datetime import UTC, datetime, timedelta
from typing import TypedDict, Unpack

import redis

from config import app_config
from redis_utils import redis_client


class LocalIdempotencyStore(dict[str, tuple[str, datetime]]):
    class SetKwargs(TypedDict, total=False):
        get: bool

    def set(self, key: str, value: str, ex: timedelta, **_kwargs: Unpack[SetKwargs]) -> str | None:
        new_value = (value, datetime.now(UTC) + ex)

        # Atomic swap
        self[key], before = new_value, self.get(key)

        before_value, expires_at = before or (
            None,
            datetime.min.replace(tzinfo=UTC),
        )

        return before_value if expires_at > datetime.now(UTC) else None


_idempotency_redis = (
    redis_client(str(app_config.redis_host)) if app_config.redis_host is not None else LocalIdempotencyStore()
)


def has_handled(
    emoji_name: str,
    event_ts: str,
    _redis: redis.Redis | LocalIdempotencyStore | None = None,
) -> bool:
    if _redis is None:
        _redis = _idempotency_redis

    observed_ts = _redis.set(
        f"emoji-papertrail:idempotency:{emoji_name}",
        event_ts,
        ex=timedelta(days=7),
        get=True,
    )

    return observed_ts == event_ts
