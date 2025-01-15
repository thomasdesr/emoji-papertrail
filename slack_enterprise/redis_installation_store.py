import json
import logging

import redis
from slack_sdk.oauth.installation_store.async_installation_store import (
    AsyncInstallationStore,
)
from slack_sdk.oauth.installation_store.installation_store import InstallationStore
from slack_sdk.oauth.installation_store.models.bot import Bot
from slack_sdk.oauth.installation_store.models.installation import Installation


class RedisInstallationStore(InstallationStore, AsyncInstallationStore):
    def __init__(
        self,
        *,
        redis_client: redis.Redis,
        client_id: str,
        key_prefix: str = "slack_installation_store",
        historical_data_enabled: bool = True,
        logger: logging.Logger | None = None,
    ) -> None:
        self.redis_client: redis.Redis = redis_client
        self.client_id: str = client_id
        self.key_prefix: str = key_prefix
        self.historical_data_enabled: bool = historical_data_enabled
        self._logger = logger

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            self._logger = logging.getLogger(__name__)
        return self._logger

    async def async_save(self, installation: Installation) -> None:
        self.save(installation)

    async def async_save_bot(self, bot: Bot) -> None:
        self.save_bot(bot)

    def save(self, installation: Installation) -> None:
        workspace_key = self._workspace_key(installation.enterprise_id, installation.team_id)
        self.save_bot(installation.to_bot())
        installation_data = json.dumps(installation.__dict__)
        self.redis_client.set(f"{workspace_key}:installer-latest", installation_data)

        if self.historical_data_enabled:
            history_version = str(installation.installed_at)
            self.redis_client.hset(
                f"{workspace_key}:installation",
                history_version,
                installation_data,
            )

    def save_bot(self, bot: Bot) -> None:
        workspace_key = self._workspace_key(bot.enterprise_id, bot.team_id)
        bot_data = json.dumps(bot.__dict__)
        self.redis_client.set(f"{workspace_key}:bot-latest", bot_data)

    def find_bot(
        self,
        *,
        enterprise_id: str | None,
        team_id: str | None,
        is_enterprise_install: bool | None = False,
    ) -> Bot | None:
        if is_enterprise_install:
            team_id = None

        workspace_key = self._workspace_key(enterprise_id, team_id)
        data = self.redis_client.get(f"{workspace_key}:bot-latest")
        if data is None:
            return None
        if not isinstance(data, bytes):
            msg = "Unexpected data type"
            raise TypeError(msg)

        return Bot(**json.loads(data))

    def find_installation(
        self,
        *,
        enterprise_id: str | None,
        team_id: str | None,
        user_id: str | None = None,  # noqa: ARG002
        is_enterprise_install: bool | None = False,
    ) -> Installation | None:
        if is_enterprise_install:
            team_id = None

        workspace_key = self._workspace_key(enterprise_id, team_id)
        data = self.redis_client.get(f"{workspace_key}:installer-latest")
        if data is None:
            return None
        if not isinstance(data, bytes):
            msg = "Unexpected data type"
            raise TypeError(msg)

        return Installation(**json.loads(data))

    def delete_bot(
        self,
        *,
        enterprise_id: str | None,
        team_id: str | None,
    ) -> None:
        workspace_key = self._workspace_key(enterprise_id, team_id)
        self.redis_client.delete(f"{workspace_key}:bot-latest")

    def delete_installation(
        self,
        *,
        enterprise_id: str | None,
        team_id: str | None,
        user_id: str | None = None,  # noqa: ARG002
    ) -> None:
        workspace_key = self._workspace_key(enterprise_id, team_id)
        self.redis_client.delete(f"{workspace_key}:installer-latest")

    def delete_all(
        self,
        *,
        enterprise_id: str | None,
        team_id: str | None,
    ) -> None:
        self.delete_bot(enterprise_id=enterprise_id, team_id=team_id)
        self.delete_installation(enterprise_id=enterprise_id, team_id=team_id)

    def _workspace_key(self, enterprise_id: str | None, team_id: str | None) -> str:
        none = "none"
        e_id = enterprise_id or none
        t_id = team_id or none
        return f"{self.key_prefix}:{self.client_id}:{e_id}-{t_id}"
