from datetime import UTC, datetime, timedelta

import redis
from redis.backoff import ExponentialBackoff
import redis.exceptions as redis_exceptions
from redis.retry import Retry

from config import config


class FakeRedis(dict[str, tuple[str, datetime]]):
    def set(self, key: str, value: str, ex: timedelta, **_kwargs: ...) -> str | None:
        new_value = (value, datetime.now(UTC) + ex)

        # Atomic swap
        self[key], before = new_value, self.get(key)

        before_value, expires_at = before or (
            None,
            datetime.min.replace(tzinfo=UTC),
        )

        return before_value if expires_at > datetime.now(UTC) else None


if config.slack_app.redis_host is not None:
    _idempotency_redis = redis.Redis.from_url(
        f"{config.slack_app.redis_host}",
        retry=Retry(ExponentialBackoff(), 3),
        retry_on_error=[
            redis_exceptions.BusyLoadingError,
            redis_exceptions.ConnectionError,
            redis_exceptions.TimeoutError,
        ],
    )
else:
    _idempotency_redis = FakeRedis()


def has_handled(
    emoji_name: str,
    event_ts: str,
    _redis: redis.Redis | FakeRedis | None = None,
) -> bool:
    if _redis is None:
        _redis = _idempotency_redis

    observed_ts = _idempotency_redis.set(
        f"emoji-papertrail:idempotency:{emoji_name}",
        event_ts,
        ex=timedelta(days=7),
        get=True,
    )

    return observed_ts == event_ts
