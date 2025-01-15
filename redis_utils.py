import redis
from redis.backoff import ExponentialBackoff
import redis.exceptions as redis_exceptions
from redis.retry import Retry


def redis_client(url: str) -> redis.Redis:
    return redis.Redis.from_url(
        url,
        retry=Retry(ExponentialBackoff(), 3),
        retry_on_error=[
            # Retry errors where our network connections to redis are being wonky
            redis_exceptions.BusyLoadingError,
            redis_exceptions.ConnectionError,
            redis_exceptions.TimeoutError,
        ],
    )
