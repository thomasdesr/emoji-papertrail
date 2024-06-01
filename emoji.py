from collections.abc import Iterable, Mapping
from typing import Optional

from pydantic import BaseModel
from slack_sdk import WebClient
import structlog

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


class EmojiInfo(BaseModel, frozen=True):
    name: str
    image_url: str
    author: str | None = None

    alias_of: Optional["EmojiInfo"] = None

    @property
    def is_alias(self) -> bool:
        return self.alias_of is not None

    def __str__(self) -> str:
        return f":{self.name}:"

    def __repr__(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_emoji_list(
        cls: type["EmojiInfo"],
        name: str,
        url: str | None,
        current_emoji_set: Mapping[str, "EmojiListEntry"],
    ) -> "EmojiInfo":
        if url is None:
            url = current_emoji_set[name].url

        alias_of = (
            cls.from_emoji_list(
                current_emoji_set[url.removeprefix("alias:")].name,
                None,
                current_emoji_set,
            )
            if url.startswith("alias:")
            else None
        )

        return cls(
            name=name,
            author=current_emoji_set[name].uploaded_by,
            image_url=url if alias_of is None else alias_of.image_url,
            alias_of=alias_of,
        )


def get_emoji(client: WebClient, name: str, url: str | None, *, is_enterprise_tenant: bool = False) -> EmojiInfo:
    log = logger.bind(emoji_name=name, emoji_url=url)

    log.info("Fetching emoji info")

    _get_emoji = _get_admin_emoji_list if is_enterprise_tenant else _get_emoji_list

    emoji_list = _get_emoji(client)

    return EmojiInfo.from_emoji_list(name, url, emoji_list)


class EmojiListEntry(BaseModel):
    name: str
    url: str
    uploaded_by: str | None = None


def _get_emoji_list(client: WebClient) -> Mapping[str, EmojiListEntry]:
    logger.info("Fetching emoji list")

    resp = client.emoji_list()

    if resp.status_code != 200:  # noqa: PLR2004
        msg = "Could not get emoji list"
        raise ValueError(msg)

    if not isinstance(resp.data, dict):
        msg = "Invalid SlackAPI response"
        raise TypeError(msg)

    if resp.data["ok"] is False:
        msg = "Could not get emoji list"
        raise ValueError(msg)

    # 🙏

    return {name: EmojiListEntry(name=name, url=url) for name, url in resp.data["emoji"].items()}


def _get_admin_emoji_list(
    client: WebClient,
) -> Mapping[str, EmojiListEntry]:
    def _pages() -> Iterable[tuple[str, EmojiListEntry]]:
        for page in client.admin_emoji_list():
            for emoji_name, emoji_info in page["emoji"].items():
                yield (
                    emoji_name,
                    EmojiListEntry.model_validate({"name": emoji_name, **emoji_info}),
                )

    return dict(_pages())
