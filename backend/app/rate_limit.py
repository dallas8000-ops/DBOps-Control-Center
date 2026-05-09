import os
import threading
import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            q = self._events[key]
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.max_requests:
                return False
            q.append(now)
            return True

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


_rate_limiter = InMemoryRateLimiter(
    max_requests=_env_int("AUTH_RATE_LIMIT_MAX_REQUESTS", 20),
    window_seconds=_env_int("AUTH_RATE_LIMIT_WINDOW_SECONDS", 60),
)


def auth_rate_limit_key(client_host: str | None, action: str) -> str:
    host = client_host or "unknown"
    return f"{action}:{host}"


def check_auth_rate_limit(client_host: str | None, action: str) -> bool:
    return _rate_limiter.allow(auth_rate_limit_key(client_host, action))


def reset_auth_rate_limit() -> None:
    _rate_limiter.clear()


def configure_auth_rate_limit(max_requests: int, window_seconds: int) -> None:
    global _rate_limiter
    _rate_limiter = InMemoryRateLimiter(max_requests=max_requests, window_seconds=window_seconds)