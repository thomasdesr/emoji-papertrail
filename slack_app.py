from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel
from slack_bolt import App
from slack_sdk import WebClient
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler
from slack_sdk.models.blocks import Block, SectionBlock
import structlog

from config import config
from emoji import EmojiInfo, get_emoji
from idemptotency import has_handled

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# Setup our Slack Webhook Handler
slack_app = App()
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
        type=payload["type"],
        subtype=payload["subtype"],
        emoji_name=payload["name"],
        emoji_url=payload["value"],
    )
    if event["subtype"] != "add":
        log.info("Ignoring non-add event")
        return {"ok": True}

    log.info("New Emoji Added!")

    emoji = get_emoji(client, payload["name"], payload["value"])

    # TODO: Figure out if we should do something more to special case alias,
    # e.g. batch/debounce the alias posts within a certain time period.
    if emoji.is_alias and not config.slack_app.should_report_alias_changes:
        log.info("Skipping alias post")
        return {"ok": True}

    if has_handled(emoji.name, payload["event_ts"]):
        log.info("Already handled, skipping")
        return {"ok": True}

    update = EmojiUpdateMessage(emoji=emoji)

    resp = client.chat_postMessage(
        channel=config.slack_app.channel,
        text=update.message(),
        blocks=update.blocks(),
    )
    log.info(
        "Posted to channel",
        channel=config.slack_app.channel,
        status_code=resp.status_code,
        data=resp.data,
    )

    return {"ok": True}


class EmojiUpdateMessage(BaseModel):
    emoji: EmojiInfo

    def message(self) -> str:
        emoji_or_alias = (
            f"alias of `{self.emoji.alias_of}`" if self.emoji.is_alias else "emoji"
        )

        if self.emoji.author is not None:
            return f"New {emoji_or_alias} added by @{self.emoji.author}!"
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
