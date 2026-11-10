"""Small single-process sliding-window limiter for authenticated operations."""

from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from time import monotonic
from typing import Annotated

from fastapi import Depends, HTTPException, Response

from shortlink.config import Settings, get_settings
from shortlink.security import require_admin


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self.clock = clock
        self._times: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, principal: str, limit: int) -> tuple[int, int]:
        with self._lock:
            now = self.clock()
            timestamps = self._times[principal]
            while timestamps and now - timestamps[0] >= 60:
                timestamps.popleft()
            remaining = max(limit - len(timestamps), 0)
            if remaining == 0:
                retry = max(1, int(60 - (now - timestamps[0])) + 1)
                return 0, retry
            timestamps.append(now)
            return remaining - 1, 0


limiter = RateLimiter()


def rate_limited_admin(
    response: Response,
    principal: Annotated[str, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    remaining, retry = limiter.check(principal, settings.max_requests_per_minute)
    if retry:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(retry),
            },
        )
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return principal
