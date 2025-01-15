import datetime
import string

import fakeredis
from hypothesis import (
    given,
    strategies as st,
)
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    consumes,
    initialize,
    rule,
)
from slack_sdk.oauth.installation_store.models.bot import Bot
from slack_sdk.oauth.installation_store.models.installation import Installation

from .redis_installation_store import RedisInstallationStore


def redis_client() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()


def installation_store(redis_client: fakeredis.FakeRedis) -> RedisInstallationStore:
    return RedisInstallationStore(
        redis_client=redis_client,
        client_id="test-client-id",
        historical_data_enabled=True,
    )


def test_save_and_find_installation() -> None:
    store = installation_store(redis_client())
    installation = Installation(
        app_id="A123",
        enterprise_id="E123",
        team_id="T123",
        user_id="U123",
        installed_at=123456789.0,
        bot_token="xoxb-123",  # noqa: S106
        bot_id="B123",
        bot_user_id="U456",
    )

    store.save(installation)
    retrieved = store.find_installation(
        enterprise_id="E123",
        team_id="T123",
        user_id="U123",
    )

    assert retrieved is not None
    assert retrieved.app_id == installation.app_id
    assert retrieved.user_id == installation.user_id


def test_save_and_find_bot() -> None:
    store = installation_store(redis_client())
    bot = Bot(
        app_id="A123",
        enterprise_id="E123",
        team_id="T123",
        bot_token="xoxb-123",  # noqa: S106
        bot_id="B123",
        bot_user_id="U456",
        installed_at=123456789.0,
    )

    store.save_bot(bot)
    retrieved = store.find_bot(
        enterprise_id="E123",
        team_id="T123",
    )

    assert retrieved is not None
    assert retrieved.bot_id == bot.bot_id
    assert retrieved.bot_user_id == bot.bot_user_id


def test_delete_installation() -> None:
    store = installation_store(redis_client())
    installation = Installation(
        app_id="A123",
        enterprise_id="E123",
        team_id="T123",
        user_id="U123",
        installed_at=123456789.0,
        bot_token="xoxb-123",  # noqa: S106
        bot_id="B123",
        bot_user_id="U456",
    )

    store.save(installation)
    store.delete_installation(enterprise_id="E123", team_id="T123")
    retrieved = store.find_installation(enterprise_id="E123", team_id="T123")

    assert retrieved is None


def test_delete_bot() -> None:
    store = installation_store(redis_client())
    bot = Bot(
        app_id="A123",
        enterprise_id="E123",
        team_id="T123",
        bot_token="xoxb-123",  # noqa: S106
        bot_id="B123",
        bot_user_id="U456",
        installed_at=123456789.0,
    )

    store.save_bot(bot)
    store.delete_bot(enterprise_id="E123", team_id="T123")
    retrieved = store.find_bot(enterprise_id="E123", team_id="T123")

    assert retrieved is None


id_text = st.text(
    min_size=4,
    max_size=10,
    alphabet=string.ascii_letters + string.digits,
)
s_app_id = id_text.map(lambda x: f"A{x}")
s_enterprise_id = id_text.map(lambda x: f"E{x}")
s_team_id = id_text.map(lambda x: f"T{x}")
s_user_id = id_text.map(lambda x: f"U{x}")
s_installed_at = st.integers(
    min_value=int(datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC).timestamp()),
    max_value=int(datetime.datetime(2030, 1, 1, tzinfo=datetime.UTC).timestamp()),
).map(float)
s_bot_token = id_text.map(lambda x: f"xoxb-{x}")
s_bot_id = id_text.map(lambda x: f"B{x}")
s_bot_user_id = id_text.map(lambda x: f"BU{x}")

s_installation = st.builds(
    Installation,
    app_id=s_app_id,
    enterprise_id=s_enterprise_id,
    team_id=s_team_id,
    user_id=s_user_id,
    installed_at=s_installed_at,
    bot_token=s_bot_token,
    bot_id=s_bot_id,
    bot_user_id=s_bot_user_id,
)

s_bot = st.builds(
    Bot,
    app_id=s_app_id,
    enterprise_id=s_enterprise_id,
    team_id=s_team_id,
    bot_token=s_bot_token,
    bot_id=s_bot_id,
    bot_user_id=s_bot_user_id,
    installed_at=s_installed_at,
)


class InstallationStoreStateMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.redis_client = fakeredis.FakeRedis()
        self.store = RedisInstallationStore(
            redis_client=self.redis_client,
            client_id="test-client-id",
            historical_data_enabled=True,
        )

    installations_bundle = Bundle("installations")
    bots_bundle = Bundle("bots")

    @initialize()
    def init_store(self) -> None:
        self.redis_client.flushall()

    @rule(
        target=installations_bundle,
        installation=s_installation,
    )
    def save_installation(self, installation: Installation) -> Installation:
        self.store.save(installation)
        return installation

    @rule(
        target=bots_bundle,
        bot=s_bot,
    )
    def save_bot(self, bot: Bot) -> Bot:
        self.store.save_bot(bot)
        return bot

    @rule(install=installations_bundle)
    def check_installation(self, install: Installation) -> None:
        retrieved = self.store.find_installation(enterprise_id=install.enterprise_id, team_id=install.team_id)
        assert retrieved is not None
        assert retrieved.to_dict() == install.to_dict()

    @rule(bot=bots_bundle)
    def check_bot(self, bot: Bot) -> None:
        retrieved = self.store.find_bot(enterprise_id=bot.enterprise_id, team_id=bot.team_id)

        assert retrieved is not None
        assert retrieved.to_dict() == bot.to_dict()

    @rule(install=consumes(installations_bundle))
    def delete_installation(self, install: Installation) -> None:
        self.store.delete_installation(enterprise_id=install.enterprise_id, team_id=install.team_id)

    @rule(bot=consumes(bots_bundle))
    def delete_bot(self, bot: Bot) -> None:
        self.store.delete_bot(enterprise_id=bot.enterprise_id, team_id=bot.team_id)


TestInstallationStoreStateMachine = InstallationStoreStateMachine.TestCase


@given(installations=st.lists(s_installation, min_size=1, max_size=10))
def test_installation_returns_latest(installations: list[Installation]) -> None:
    """Test that when multiple installations are saved, the latest one is returned."""
    store = installation_store(redis_client())

    # Sort installations by installed_at time and save them
    sorted_installations = sorted(installations, key=lambda x: x.installed_at)
    for installation in sorted_installations:
        store.save(installation)

    last_installation = sorted_installations[-1]

    # Should find the latest installation
    retrieved = store.find_installation(
        enterprise_id=last_installation.enterprise_id,
        team_id=last_installation.team_id,
    )

    assert retrieved is not None
    assert retrieved.installed_at == last_installation.installed_at
    assert retrieved.to_dict() == last_installation.to_dict()
