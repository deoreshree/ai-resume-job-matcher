"""Minimal best-effort in-memory rate limiter (no external services).

Suitable for single-process or small multi-worker deployments where perfect
global accuracy is not required. Set ``RATE_LIMIT_PER_MINUTE=0`` to disable.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict


class RateLimiter:
    """Sliding-window per-key request limiter."""

    def __init__(self, max_requests: int = 0, window_seconds: float = 60.0):
        self.max_requests = max(0, int(max_requests))
        self.window_seconds = float(window_seconds)
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.max_requests > 0

    def allow(self, key: str, now: float | None = None) -> bool:
        """Record a request for ``key`` and return whether it is allowed."""
        if not self.enabled:
            return True
        moment = time.monotonic() if now is None else now
        cutoff = moment - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(moment)
            return True

    def retry_after(self, key: str, now: float | None = None) -> int:
        """Seconds until the oldest recorded hit leaves the window (>= 1)."""
        moment = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.get(key)
            if not hits:
                return 1
            return max(1, int(hits[0] + self.window_seconds - moment) + 1)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
