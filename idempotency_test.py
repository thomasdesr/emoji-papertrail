from datetime import timedelta

import time_machine

from idemptotency import has_handled


def test_has_handled():
    with time_machine.travel(0, tick=False) as tm:
        assert has_handled("test", "12345") is False, "First time we see an emoji, it should always be false"

        assert has_handled("test", "12345") is True, (
            "Second time we see an emoji, without any time advancement, we should say we've seen it too recently"
        )

        # Advance time forward by 10 seconds
        tm.shift(timedelta(days=14))

        assert has_handled("test", "12345") is False, "After advancing time, it should go back to being false"
