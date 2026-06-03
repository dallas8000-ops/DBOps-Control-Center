import logging
import os
import threading
import time
from collections import defaultdict, deque
from typing import Protocol

logger = logging.getLogger(__name__)


class RateLimiter(Protocol):
    def allow(self, key: str) -> bool: ...

    def clear(self) -> None: ...


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


class RedisRateLimiter:
    """Fixed-window counter shared across API replicas when REDIS_URL is set."""

    def __init__(self, redis_url: str, max_requests: int, window_seconds: int):
        import redis

        self.client = redis.from_url(redis_url, decode_responses=True)
        self.client.ping()
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._prefix = "dbops:rl"

    def allow(self, key: str) -> bool:
        bucket = int(time.time()) // self.window_seconds
        redis_key = f"{self._prefix}:{key}:{bucket}"
        count = self.client.incr(redis_key)
        if count == 1:
            self.client.expire(redis_key, self.window_seconds + 1)
        return count <= self.max_requests

    def clear(self) -> None:
        for key in self.client.scan_iter(f"{self._prefix}:*"):
            self.client.delete(key)


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _build_limiter(max_requests: int, window_seconds: int) -> RateLimiter:
    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        try:
            return RedisRateLimiter(redis_url, max_requests, window_seconds)
        except Exception as exc:
            logger.warning("Redis rate limit unavailable (%s); using in-memory limits", exc)
    return InMemoryRateLimiter(max_requests=max_requests, window_seconds=window_seconds)


_rate_limiter = _build_limiter(
    max_requests=_env_int("AUTH_RATE_LIMIT_MAX_REQUESTS", 20),
    window_seconds=_env_int("AUTH_RATE_LIMIT_WINDOW_SECONDS", 60),
)
_api_rate_limiter = _build_limiter(
    max_requests=_env_int("API_RATE_LIMIT_MAX_REQUESTS", 120),
    window_seconds=_env_int("API_RATE_LIMIT_WINDOW_SECONDS", 60),
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


def api_rate_limit_key(client_host: str | None, bucket: str) -> str:
    host = client_host or "unknown"
    return f"api:{bucket}:{host}"


def check_api_rate_limit(client_host: str | None, bucket: str) -> bool:
    return _api_rate_limiter.allow(api_rate_limit_key(client_host, bucket))


def reset_api_rate_limit() -> None:
    _api_rate_limiter.clear()


def configure_api_rate_limit(max_requests: int, window_seconds: int) -> None:
    global _api_rate_limiter
    _api_rate_limiter = InMemoryRateLimiter(max_requests=max_requests, window_seconds=window_seconds)


def rate_limit_backend_name() -> str:
    if isinstance(_rate_limiter, RedisRateLimiter) and isinstance(_api_rate_limiter, RedisRateLimiter):
        return "redis"
    if isinstance(_rate_limiter, InMemoryRateLimiter) and isinstance(_api_rate_limiter, InMemoryRateLimiter):
        return "memory"
    return "mixed"
