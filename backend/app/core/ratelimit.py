"""slowapi limiter, per-user keys and a lightweight WebSocket guard."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
    storage_uri=settings.rate_limit_storage_uri,
    headers_enabled=False,
)


def user_or_ip(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        import hashlib

        return hashlib.sha256(auth[7:].encode()).hexdigest()[:24]
    return get_remote_address(request)


class SocketRateGuard:
    """In-process sliding window for WebSocket messages (per connection)."""

    def __init__(self, limit: int = 60, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window = window_seconds
        self.events: deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        while self.events and now - self.events[0] > self.window:
            self.events.popleft()
        if len(self.events) >= self.limit:
            return False
        self.events.append(now)
        return True


_hint_counts: defaultdict[str, int] = defaultdict(int)


def note_hint(interview_id: str) -> int:
    _hint_counts[interview_id] += 1
    return _hint_counts[interview_id]
