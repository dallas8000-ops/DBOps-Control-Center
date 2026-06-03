import re

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS = Counter(
    "dbops_http_requests_total",
    "Total HTTP requests processed by the API",
    ["method", "route", "status_class"],
)
LATENCY = Histogram(
    "dbops_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


def normalize_route(path: str) -> str:
    normalized = path.split("?", 1)[0]
    return re.sub(r"/\d+", "/{id}", normalized)


def record_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    route = normalize_route(path)
    status_class = f"{status_code // 100}xx"
    REQUESTS.labels(method=method, route=route, status_class=status_class).inc()
    LATENCY.labels(method=method, route=route).observe(duration_seconds)


def metrics_enabled() -> bool:
    import os

    return os.getenv("METRICS_ENABLED", "1").strip().lower() not in {"0", "false", "no"}


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
