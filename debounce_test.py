from datetime import timedelta

import time_machine

from debounce import seen_too_recently
from emoji import EmojiInfo


def test_seen_too_recently():
    emoji = EmojiInfo(name="test", image_url="https://example.com/test.png")

    def too_recently() -> bool:
        return seen_too_recently(
            emoji,
            timedelta(seconds=5),
        )

    with time_machine.travel(0, tick=False) as tm:
        assert (
            too_recently() is False
        ), "First time we see an emoji, it should always be false"

        assert (
            too_recently() is True
        ), "Second time we see an emoji, without any time advancement, we should say we've seen it too recently"

        # Advance time forward by 10 seconds
        tm.shift(timedelta(seconds=10))

        assert (
            too_recently() is False
        ), "After advancing time, it should go back to being false"
