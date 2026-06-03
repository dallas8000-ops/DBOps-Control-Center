from types import SimpleNamespace

from app.main import app
from fastapi.testclient import TestClient


def test_metrics_endpoint_returns_prometheus_payload() -> None:
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "dbops_http_requests_total" in resp.text


def test_health_observability_reports_backend() -> None:
    client = TestClient(app)
    resp = client.get("/health/observability")
    assert resp.status_code == 200
    body = resp.json()
    assert body["metrics_enabled"] is True
    assert body["metrics_path"] == "/metrics"
    assert body["rate_limit_backend"] in {"memory", "redis", "mixed"}
