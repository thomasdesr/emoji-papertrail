from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel
from slack_bolt import App as SlackApp
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk import WebClient
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler
from slack_sdk.models.blocks import Block, SectionBlock
import structlog

from config import BotTokenConfig, SlackOAuthConfig, app_config, app_credentials
from emoji import EmojiInfo, get_emoji
from idemptotency import has_handled
from redis_utils import redis_client
from slack_enterprise.redis_installation_store import RedisInstallationStore
from slack_enterprise.redis_oauth_state_store import RedisOAuthStateStore

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


_slack_app_cfg = {}
if isinstance(app_credentials, SlackOAuthConfig):
    _oauth_redis = redis_client(str(app_config.redis_host))

    _slack_app_cfg["oauth_settings"] = OAuthSettings(
        client_id=app_credentials.client_id.get_secret_value(),
        client_secret=app_credentials.client_secret.get_secret_value(),
        scopes=app_credentials.bot_scopes,
        user_scopes=app_credentials.user_scopes,
        installation_store=RedisInstallationStore(
            redis_client=_oauth_redis,
            client_id=app_credentials.client_id.get_secret_value(),
        ),
        state_store=RedisOAuthStateStore(
            redis_client=_oauth_redis,
            expiration_seconds=600,
        ),
    )
elif isinstance(app_credentials, BotTokenConfig):
    _slack_app_cfg["token"] = app_credentials.token


# Setup our Slack Webhook Handler
slack_app = SlackApp(
    **_slack_app_cfg,
)
slack_app.client.retry_handlers.append(
    # Ensure we follow the backoff instructions
    RateLimitErrorRetryHandler(
        # But strong prefer not to drop these, lol
        max_retry_count=5,
    ),
)


@slack_app.event("emoji_changed")
def emoji_changed(
    client: WebClient,
    event: Mapping[str, Any],
    context: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    """{
        'event_ts': '1671070007.348400',
        'name': 'test-emoji-pls-ignore-1',
        'subtype': 'add',
        'type': 'emoji_changed',
        'value': 'https://emoji.slack-edge.com/EXAMPLE/test-emoji-pls-ignore-1/0da8457a872dfe8a.png',
    }
    """
    log = logger.bind(
        event=event,
        payload=payload,
        **{k: v for k, v in payload.items() if k in ("name", "subtype", "type", "value")},
    )
    if event["subtype"] != "add":
        log.info("Ignoring non-add event")
        return {"ok": True}

    log.info("New Emoji Added!")

    user_client = WebClient(token=context["user_token"])
    emoji = get_emoji(
        user_client,
        payload["name"],
        payload["value"],
        is_enterprise_tenant=context.get("is_enterprise_install", False),
    )

    # TODO: Figure out if we should do something more to special case alias,
    # e.g. batch/debounce the alias posts within a certain time period.
    if emoji.is_alias and not app_config.should_report_alias_changes:
        log.info("Skipping alias post")
        return {"ok": True}

    if has_handled(emoji.name, payload["event_ts"]):
        log.info("Already handled, skipping")
        return {"ok": True}

    update = EmojiUpdateMessage(emoji=emoji)

    resp = client.chat_postMessage(
        channel=app_config.channel,
        text=update.message(),
        blocks=update.blocks(),
    )
    log.info(
        "Posted to channel",
        channel=app_config.channel,
        status_code=resp.status_code,
        data=resp.data,
    )

    return {"ok": True}


class EmojiUpdateMessage(BaseModel):
    emoji: EmojiInfo

    def message(self) -> str:
        emoji_or_alias = f"alias of `{self.emoji.alias_of}`" if self.emoji.is_alias else "emoji"

        if self.emoji.author is not None:
            return f"New {emoji_or_alias} added by <@{self.emoji.author}>!"
        return f"New {emoji_or_alias} added!"

    # TODO: Type this at some point
    def blocks(self) -> list[Block]:
        primary_block = SectionBlock(
            text={
                "text": self.message(),
                "type": "mrkdwn",
            },
            fields=[
                {"type": "mrkdwn", "text": "*Name*"},
                {"type": "mrkdwn", "text": "*Emoji*"},
                {"type": "mrkdwn", "text": f"`{self.emoji}`"},
                {"type": "mrkdwn", "text": str(self.emoji)},
            ],
            accessory={
                "type": "image",
                "image_url": self.emoji.image_url,
                "alt_text": str(self.emoji),
            },
        )

        return [primary_block]
