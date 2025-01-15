import logging
from uuid import uuid4

from redis import Redis
from slack_sdk.oauth.state_store import OAuthStateStore


class RedisOAuthStateStore(OAuthStateStore):
    def __init__(
        self,
        redis_client: Redis,
        expiration_seconds: int,
        key_prefix: str = "slack_oauth_state_store",
        logger: logging.Logger | None = None,
    ) -> None:
        self.redis_client = redis_client
        self.expiration_seconds = expiration_seconds
        self.key_prefix = key_prefix
        self._logger = logger

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            self._logger = logging.getLogger(__name__)
        return self._logger

    def issue(self, *_args: ..., **_kwargs: ...) -> str:
        state: str = str(uuid4())
        self.redis_client.setex(
            name=self._state_key(state),
            time=self.expiration_seconds,
            value="1",
        )
        return state

    def consume(self, state: str) -> bool:
        consumed = self.redis_client.delete(self._state_key(state))
        return consumed == 1

    def _state_key(self, state: str) -> str:
        return f"{self.key_prefix}:{state}"
