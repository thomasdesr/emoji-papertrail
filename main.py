import random
import secrets
import string
import time
from typing import Any, List, Mapping

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler
import structlog


# isort: off
from emoji import EmojiInfo, get_emoji


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

# Setup our slack slack
slack_app = App()
slack_app.client.retry_handlers.append(
    # Ensure we follow the backoff instructions
    RateLimitErrorRetryHandler(max_retry_count=3)
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

    # TODO: Figure out if we should special case aliases (e.g. skip them)
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
        if self.emoji.is_alias:
            emoji_or_alias = f"alias of `{self.emoji.alias_of}`"
        else:
            emoji_or_alias = "emoji"

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


# Setup FastAPI & have it serve the Slack app
app = FastAPI()
slack_app_handler = SlackRequestHandler(slack_app)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    log = logger.bind(
        request_id=secrets.token_urlsafe(),
        source=f"{request.client.host}:{request.client.port}"
        if request.client
        else "unknown",
        host=request.url.hostname,
        path=request.url.path,
        method=request.method,
    )

    log.info("Request: Start")
    start_time = time.monotonic()

    response: Response = await call_next(request)

    process_time = (time.monotonic() - start_time) * 1000

    log.info(
        "Request: Stop",
        status_code=response.status_code,
        process_time="{0:.2f}ms".format(process_time),
    )

    return response


@app.post("/slack/events")
async def handle_slack_event(request: Request):
    return await slack_app_handler.handle(request)
