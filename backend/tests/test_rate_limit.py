from app.rate_limit import InMemoryRateLimiter, RedisRateLimiter


class FakeRedisClient:
    def __init__(self):
        self.store: dict[str, int] = {}

    def ping(self) -> bool:
        return True

    def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key: str, ttl: int) -> None:
        _ = (key, ttl)

    def scan_iter(self, pattern: str):
        prefix = pattern.replace("*", "")
        for key in list(self.store):
            if key.startswith(prefix.rstrip("*")):
                yield key

    def delete(self, key: str) -> None:
        self.store.pop(key, None)


def test_redis_rate_limiter_blocks_after_max_requests() -> None:
    fake = FakeRedisClient()
    limiter = RedisRateLimiter.__new__(RedisRateLimiter)
    limiter.client = fake
    limiter.max_requests = 2
    limiter.window_seconds = 60
    limiter._prefix = "dbops:rl"

    assert limiter.allow("auth-login:127.0.0.1") is True
    assert limiter.allow("auth-login:127.0.0.1") is True
    assert limiter.allow("auth-login:127.0.0.1") is False


def test_in_memory_rate_limiter_still_blocks_after_max_requests() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("bucket") is True
    assert limiter.allow("bucket") is True
    assert limiter.allow("bucket") is False
