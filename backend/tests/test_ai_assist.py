import os
from collections.abc import Generator
from math import isclose

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.rate_limit import configure_api_rate_limit, configure_auth_rate_limit, reset_api_rate_limit, reset_auth_rate_limit


PASSWORD_FIELD = "password"
PRIMARY_SECRET = "Password123!"


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login_token(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/auth/login", json={"email": email, PASSWORD_FIELD: password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _bootstrap_dba(client: TestClient) -> str:
    payload = {"email": "dba@example.com", PASSWORD_FIELD: PRIMARY_SECRET, "role": "DBA"}
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    return _login_token(client, payload["email"], payload["password"])


def _create_user(client: TestClient, dba_token: str, email: str, role: str) -> None:
    resp = client.post(
        "/auth/users",
        json={"email": email, PASSWORD_FIELD: PRIMARY_SECRET, "role": role},
        headers=_auth_headers(dba_token),
    )
    assert resp.status_code == 201


def _client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    configure_auth_rate_limit(max_requests=1000, window_seconds=60)
    reset_auth_rate_limit()
    configure_api_rate_limit(max_requests=1000, window_seconds=60)
    reset_api_rate_limit()
    app.dependency_overrides[get_db] = override_get_db
    old_disable_scheduler = os.environ.get("SCHEDULED_REPORTS_DISABLE_LOOP")
    os.environ["SCHEDULED_REPORTS_DISABLE_LOOP"] = "1"
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    if old_disable_scheduler is None:
        os.environ.pop("SCHEDULED_REPORTS_DISABLE_LOOP", None)
    else:
        os.environ["SCHEDULED_REPORTS_DISABLE_LOOP"] = old_disable_scheduler
    reset_auth_rate_limit()
    reset_api_rate_limit()
    Base.metadata.drop_all(bind=engine)


def test_ai_find_report_enforces_role_visible_catalog(monkeypatch) -> None:
    monkeypatch.setattr("app.main._llm_report_match", lambda *_args, **_kwargs: None)

    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "viewer@example.com", "Viewer")
        viewer_token = _login_token(client, "viewer@example.com", "Password123!")

        resp = client.post(
            "/api/ai/find-report",
            json={"user_query": "show report runs by report key and admin audit actions"},
            headers=_auth_headers(viewer_token),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["report_key"] in {
            "incidents_by_status",
            "incidents_recent",
            "incidents_open_by_owner",
            "incidents_by_severity",
        }
        assert body["report_key"] not in {"report_runs_by_report_key", "admin_audit_by_action", "users_by_role"}


def test_ai_find_report_returns_llm_match_when_available(monkeypatch) -> None:
    from app.schemas import AiFindReportResponse

    monkeypatch.setattr(
        "app.main._llm_report_match",
        lambda *_args, **_kwargs: AiFindReportResponse(
            report_key="incidents_recent",
            title="Recent incidents",
            description="Latest incidents ordered by created_at (bounded limit).",
            matched_by="llm",
            confidence=0.94,
        ),
    )

    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")

        resp = client.post(
            "/api/ai/find-report",
            json={"user_query": "show me the latest incident entries"},
            headers=_auth_headers(analyst_token),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["report_key"] == "incidents_recent"
        assert body["matched_by"] == "llm"
        assert isclose(body["confidence"], 0.94, rel_tol=0.0, abs_tol=1e-9)


def test_ai_summarize_incident_not_found() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "viewer@example.com", "Viewer")
        viewer_token = _login_token(client, "viewer@example.com", "Password123!")

        resp = client.post(
            "/api/ai/summarize-incident/999",
            json={},
            headers=_auth_headers(viewer_token),
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Incident not found"


def test_ai_summarize_incident_returns_three_line_heuristic(monkeypatch) -> None:
    monkeypatch.setattr("app.main._llm_incident_summary", lambda *_args, **_kwargs: None)

    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        _create_user(client, dba_token, "viewer@example.com", "Viewer")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")
        viewer_token = _login_token(client, "viewer@example.com", "Password123!")

        create_resp = client.post(
            "/incidents",
            json={
                "title": "Queue depth spike",
                "description": "Background queue depth rose quickly on primary",
                "severity": "high",
                "owner": "analyst@example.com",
            },
            headers=_auth_headers(analyst_token),
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["id"]

        summary_resp = client.post(
            f"/api/ai/summarize-incident/{incident_id}",
            json={},
            headers=_auth_headers(viewer_token),
        )

        assert summary_resp.status_code == 200
        body = summary_resp.json()
        assert body["incident_id"] == incident_id
        assert body["source"] == "heuristic"
        assert len(body["summary_lines"]) == 3
        assert all(isinstance(line, str) and line.strip() for line in body["summary_lines"])
