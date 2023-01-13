from typing import Any, List, Mapping

from pydantic import BaseModel
from slack_bolt import App
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler
import structlog

from emoji import EmojiInfo, get_emoji

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# Setup our Slack Webhook Handler
slack_app = App()
slack_app.client.retry_handlers.append(
    # Ensure we follow the backoff instructions
    RateLimitErrorRetryHandler(
        # But strong prefer not to drop these, lol
        max_retry_count=5
    )
)


@slack_app.event({"type": "emoji_changed", "subtype": "add"})
def emoji_changed(client, event, payload):
    """{
        'event_ts': '1671070007.348400',
        'name': 'test-emoji-pls-ignore-1',
        'subtype': 'add',
        'type': 'emoji_changed',
        'value': 'https://emoji.slack-edge.com/EXAMPLE/test-emoji-pls-ignore-1/0da8457a872dfe8a.png',
    }"""
    log = logger.bind(
        event=event,
        payload=payload,
        type=payload["type"],
        subtype=payload["subtype"],
        emoji_name=payload["name"],
        emoji_url=payload["value"],
    )
    log.info("New Emoji Added!")

    emoji = get_emoji(client, payload["name"], payload["value"])

    # TODO: Figure out if we should special case aliases:
    # * Let users configure if they want to post about aliases
    # * Batch/debounce the alias posts
    update = EmojiUpdateMessage(emoji=emoji)

    resp = client.chat_postMessage(
        channel="#emoji-papertrail",
        text=update.message(),
        blocks=update.blocks(),
    )
    log.info("Posted to channel", status_code=resp.status_code, data=resp.data)

    return {"ok": True}


class EmojiUpdateMessage(BaseModel):
    emoji: EmojiInfo

    def message(self) -> str:
        emoji_or_alias = (
            f"alias of `{self.emoji.alias_of}`" if self.emoji.is_alias else "emoji"
        )

        if self.emoji.author is not None:
            return f"New {emoji_or_alias} added by @{self.emoji.author}!"
        else:
            return f"New {emoji_or_alias} added!"

    # TODO: Type this at some point
    def blocks(self) -> List[Mapping[str, Any]]:
        primary_block = {
            "type": "section",
            "text": {
                "text": self.message(),
                "type": "mrkdwn",
            },
            "fields": [
                {"type": "mrkdwn", "text": "*Name*"},
                {"type": "mrkdwn", "text": "*Emoji*"},
                {"type": "mrkdwn", "text": f"`{self.emoji}`"},
                {"type": "mrkdwn", "text": str(self.emoji)},
            ],
            "accessory": {
                "type": "image",
                "image_url": self.emoji.image_url,
                "alt_text": str(self.emoji),
            },
        }

        return [primary_block]
