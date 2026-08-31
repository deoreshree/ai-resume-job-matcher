"""Tests for the in-memory rate limiter."""

from __future__ import annotations

from utils.rate_limit import RateLimiter


def test_allows_up_to_limit_within_window():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    t0 = 1_000.0
    assert all(limiter.allow("ip-1", t0 + i) for i in range(3))
    assert not limiter.allow("ip-1", t0 + 3)


def test_keys_are_independent():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.allow("a", 10.0)
    assert limiter.allow("b", 10.0)
    assert not limiter.allow("a", 10.5)


def test_window_slides():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("ip", 0.0)
    assert limiter.allow("ip", 30.0)
    assert not limiter.allow("ip", 45.0)
    assert limiter.allow("ip", 61.0)  # first hit expired


def test_disabled_when_zero():
    limiter = RateLimiter(max_requests=0)
    assert not limiter.enabled
    assert all(limiter.allow("ip", i) for i in range(100))


def test_retry_after_positive():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.allow("ip", 0.0)
    assert limiter.retry_after("ip", 1.0) >= 1
