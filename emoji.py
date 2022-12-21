from typing import Mapping, Optional

from pydantic import BaseModel
from slack_sdk import WebClient
import structlog


logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class EmojiInfo(BaseModel):
    name: str
    image_url: str
    author: Optional[str] = None

    alias_of: Optional["EmojiInfo"] = None

    @property
    def is_alias(self) -> bool:
        return self.alias_of is not None

    def __str__(self) -> str:
        return f":{self.name}:"


def get_emoji(client: WebClient, name: str, url: Optional[str]) -> EmojiInfo:
    log = logger.bind(emoji_name=name, emoji_url=url)

    log.info("Fetching emoji")

    # When we can, avoid sending the extra API call. Eventually when we want to
    # support pulling the author of the emoji we'll need to do this on every
    # call afaik. This should be optional depending on if the Slack Org has
    # the enterprise APIs.
    if url is None:
        log.info("No emoji URL provided, fetching from API")
        emoji_list = _get_emoji_list(client)

        url = emoji_list[name]

    if url.startswith("alias:"):
        log.info("Emoji is an alias, fetching aliased emoji")

        aliased_emoji = get_emoji(client, url.removeprefix("alias:"), None)

        return EmojiInfo(
            name=name,
            image_url=aliased_emoji.image_url,
            alias_of=aliased_emoji,
        )
    else:
        return EmojiInfo(
            name=name,
            image_url=url,
        )


# TODO: Figure out a caching story for this? It seems expensive to call this
# every time but nearly every time we need to call this a new emoji was created
# and so we're gonna need to bust the cache anyways. Hopefully the builtin
# RateLimitErrorRetryHandler will be good enough.
def _get_emoji_list(client: WebClient) -> Mapping[str, str]:
    logger.info("Fetching emoji list")

    resp = client.emoji_list()

    if resp.status_code != 200:
        raise ValueError("Could not get emoji list")

    if not isinstance(resp.data, dict):
        raise TypeError("Invalid slackAPI response")

    if resp.data["ok"] is False:
        raise ValueError("Could not get emoji list")

    return resp.data["emoji"]
