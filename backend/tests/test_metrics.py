import os

from app.main import app
from fastapi.testclient import TestClient


def test_metrics_endpoint_requires_credentials(monkeypatch) -> None:
    monkeypatch.delenv("METRICS_BEARER_TOKEN", raising=False)
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 401


def test_metrics_endpoint_returns_prometheus_payload_with_bearer(monkeypatch) -> None:
    monkeypatch.setenv("METRICS_BEARER_TOKEN", "test-metrics-secret")
    client = TestClient(app)
    resp = client.get("/metrics", headers={"Authorization": "Bearer test-metrics-secret"})
    assert resp.status_code == 200
    assert "dbops_http_requests_total" in resp.text


def test_metrics_endpoint_allows_dba_jwt(monkeypatch) -> None:
    from tests.test_auth_rbac import PRIMARY_SECRET, _bootstrap_dba, _client

    monkeypatch.delenv("METRICS_BEARER_TOKEN", raising=False)
    for client in _client():
        _bootstrap_dba(client)
        login = client.post(
            "/auth/login",
            json={"email": "dba@example.com", "password": PRIMARY_SECRET},
        )
        token = login.json()["access_token"]
        resp = client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
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
