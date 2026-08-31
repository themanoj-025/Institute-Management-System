"""Tests for api.rate_limiter — SlidingWindowCounter."""

import time

from api.rate_limiter import SlidingWindowCounter


class TestSlidingWindowCounter:
    """Test the sliding-window rate limiter."""

    def test_allows_first_request(self) -> None:
        sw = SlidingWindowCounter(max_requests=5, window_seconds=60)
        allowed, remaining, _ = sw.allow("ip1")
        assert allowed is True
        assert remaining == 4

    def test_allows_up_to_max(self) -> None:
        sw = SlidingWindowCounter(max_requests=3, window_seconds=60)
        for i in range(3):
            allowed, _, _ = sw.allow("ip1")
            assert allowed is True
        allowed, remaining, _ = sw.allow("ip1")
        assert allowed is False
        assert remaining == 0

    def test_different_keys_independent(self) -> None:
        sw = SlidingWindowCounter(max_requests=2, window_seconds=60)
        sw.allow("ip1")
        sw.allow("ip1")
        allowed, _, _ = sw.allow("ip1")
        assert allowed is False
        allowed, _, _ = sw.allow("ip2")
        assert allowed is True

    def test_window_expiry(self) -> None:
        sw = SlidingWindowCounter(max_requests=2, window_seconds=0.1)
        sw.allow("ip1")
        sw.allow("ip1")
        allowed, _, _ = sw.allow("ip1")
        assert allowed is False
        time.sleep(0.15)
        allowed, remaining, _ = sw.allow("ip1")
        assert allowed is True

    def test_remaining_never_negative(self) -> None:
        sw = SlidingWindowCounter(max_requests=1, window_seconds=60)
        sw.allow("ip1")
        allowed, remaining, _ = sw.allow("ip1")
        assert allowed is False
        assert remaining >= 0

    def test_reset_after_positive(self) -> None:
        sw = SlidingWindowCounter(max_requests=1, window_seconds=60)
        allowed, _, reset_after = sw.allow("ip1")
        assert reset_after > 0
