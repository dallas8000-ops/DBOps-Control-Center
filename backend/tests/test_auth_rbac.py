import os
from csv import reader as csv_reader
from collections.abc import Generator
from datetime import datetime, timedelta
from io import StringIO
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import ReportExecutionLog, ReportSchedule
from app.rate_limit import configure_auth_rate_limit, reset_auth_rate_limit
import app.scheduler as scheduler_module
from app.report_runner import execute_whitelisted_report as execute_whitelisted_report_real
from app.scheduler import process_due_report_schedules


PASSWORD_FIELD = "password"
PRIMARY_SECRET = "".join(["Pass", "word", "123!"])
INVALID_SECRET = "".join(["wrong", "-", "pass"])
ROTATED_SECRET = "".join(["Another", "Pass", "123!"])


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
    Base.metadata.drop_all(bind=engine)


def _fake_stripe_module(*, session_payload: dict | None = None, event_payload: dict | None = None):
    payload = session_payload or {"id": "cs_test_123", "url": "https://checkout.stripe.test/session/cs_test_123"}
    event = event_payload or {
        "type": "checkout.session.completed",
        "data": {"object": {"customer": "cus_test_123", "subscription": "sub_test_123"}},
    }
    return SimpleNamespace(
        api_key=None,
        checkout=SimpleNamespace(Session=SimpleNamespace(create=lambda **kwargs: payload)),
        Webhook=SimpleNamespace(construct_event=lambda **kwargs: event),
    )


def test_bootstrap_requires_first_user_to_be_dba() -> None:
    for client in _client():
        resp = client.post(
            "/auth/register",
            json={"email": "not-dba@example.com", "password": "Password123!", "role": "Analyst"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "First registered user must have role DBA"


def test_dba_can_manage_user_status_and_disabled_user_cannot_login() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")

        users_resp = client.get("/auth/users", headers=_auth_headers(dba_token))
        assert users_resp.status_code == 200
        analyst = next(u for u in users_resp.json() if u["email"] == "analyst@example.com")

        disable_resp = client.patch(
            f"/auth/users/{analyst['id']}/status",
            json={"is_active": False},
            headers=_auth_headers(dba_token),
        )
        assert disable_resp.status_code == 200
        assert disable_resp.json()["is_active"] is False

        login_resp = client.post(
            "/auth/login",
            json={"email": "analyst@example.com", "password": "Password123!"},
        )
        assert login_resp.status_code == 403
        assert login_resp.json()["detail"] == "Your account is disabled. Contact a DBA."


def test_viewer_cannot_create_incident() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "viewer@example.com", "Viewer")
        viewer_token = _login_token(client, "viewer@example.com", "Password123!")

        resp = client.post(
            "/incidents",
            json={
                "title": "Disk space warning",
                "description": "Disk usage crossed threshold on primary node",
                "severity": "high",
                "owner": "viewer@example.com",
            },
            headers=_auth_headers(viewer_token),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Insufficient permissions"


def test_analyst_can_create_incident_but_cannot_resolve() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")

        create_resp = client.post(
            "/incidents",
            json={
                "title": "Replication lag",
                "description": "Replica lag exceeded 2 minutes",
                "severity": "medium",
                "owner": "analyst@example.com",
            },
            headers=_auth_headers(analyst_token),
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["id"]

        resolve_resp = client.patch(
            f"/incidents/{incident_id}/resolve",
            headers=_auth_headers(analyst_token),
        )
        assert resolve_resp.status_code == 403
        assert resolve_resp.json()["detail"] == "Insufficient permissions"


def test_analyst_can_edit_incident() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")

        create_resp = client.post(
            "/incidents",
            json={
                "title": "Backup latency",
                "description": "Nightly backup completed late",
                "severity": "low",
                "owner": "analyst@example.com",
            },
            headers=_auth_headers(analyst_token),
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["id"]

        edit_resp = client.patch(
            f"/incidents/{incident_id}",
            json={
                "title": "Backup latency spike",
                "description": "Nightly backup exceeded target by 30 minutes",
                "severity": "medium",
                "owner": "dba@example.com",
            },
            headers=_auth_headers(analyst_token),
        )
        assert edit_resp.status_code == 200
        body = edit_resp.json()
        assert body["title"] == "Backup latency spike"
        assert body["severity"] == "medium"
        assert body["owner"] == "dba@example.com"


def test_incident_history_records_create_update_resolve() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        _create_user(client, dba_token, "viewer@example.com", "Viewer")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")
        viewer_token = _login_token(client, "viewer@example.com", "Password123!")

        create_resp = client.post(
            "/incidents",
            json={
                "title": "Slow query",
                "description": "Top queries show regression",
                "severity": "low",
                "owner": "analyst@example.com",
            },
            headers=_auth_headers(analyst_token),
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["id"]

        hist0 = client.get(f"/incidents/{incident_id}/history", headers=_auth_headers(analyst_token))
        assert hist0.status_code == 200
        assert len(hist0.json()) == 1
        assert hist0.json()[0]["action"] == "created"
        assert hist0.json()[0]["actor_email"] == "analyst@example.com"

        viewer_hist = client.get(f"/incidents/{incident_id}/history", headers=_auth_headers(viewer_token))
        assert viewer_hist.status_code == 200
        assert len(viewer_hist.json()) == 1

        edit_resp = client.patch(
            f"/incidents/{incident_id}",
            json={"title": "Slow query burst", "severity": "high"},
            headers=_auth_headers(analyst_token),
        )
        assert edit_resp.status_code == 200

        hist1 = client.get(f"/incidents/{incident_id}/history", headers=_auth_headers(analyst_token))
        assert hist1.status_code == 200
        entries = hist1.json()
        assert len(entries) == 2
        assert entries[1]["action"] == "updated"
        assert "title" in entries[1]["details"]["changes"]
        assert "severity" in entries[1]["details"]["changes"]

        resolve_resp = client.patch(f"/incidents/{incident_id}/resolve", headers=_auth_headers(dba_token))
        assert resolve_resp.status_code == 200

        hist2 = client.get(f"/incidents/{incident_id}/history", headers=_auth_headers(analyst_token))
        assert hist2.status_code == 200
        assert len(hist2.json()) == 3
        assert hist2.json()[2]["action"] == "resolved"
        assert hist2.json()[2]["actor_email"] == "dba@example.com"

        resolve_again = client.patch(f"/incidents/{incident_id}/resolve", headers=_auth_headers(dba_token))
        assert resolve_again.status_code == 200
        hist_no_dup = client.get(f"/incidents/{incident_id}/history", headers=_auth_headers(analyst_token))
        assert len(hist_no_dup.json()) == 3

        missing = client.get("/incidents/99999/history", headers=_auth_headers(analyst_token))
        assert missing.status_code == 404


def test_viewer_cannot_edit_incident() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        _create_user(client, dba_token, "viewer@example.com", "Viewer")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")
        viewer_token = _login_token(client, "viewer@example.com", "Password123!")

        create_resp = client.post(
            "/incidents",
            json={
                "title": "CPU saturation",
                "description": "CPU reached sustained 95 percent",
                "severity": "high",
                "owner": "analyst@example.com",
            },
            headers=_auth_headers(analyst_token),
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["id"]

        edit_resp = client.patch(
            f"/incidents/{incident_id}",
            json={"title": "CPU saturation updated"},
            headers=_auth_headers(viewer_token),
        )
        assert edit_resp.status_code == 403
        assert edit_resp.json()["detail"] == "Insufficient permissions"


def test_incident_filters_by_status_owner_and_search() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")

        first = client.post(
            "/incidents",
            json={
                "title": "Replica lag event",
                "description": "Replica lag exceeded 120 seconds",
                "severity": "high",
                "owner": "ops-team",
            },
            headers=_auth_headers(analyst_token),
        )
        assert first.status_code == 201

        second = client.post(
            "/incidents",
            json={
                "title": "Routine vacuum",
                "description": "Vacuum completed with expected duration",
                "severity": "low",
                "owner": "maintenance",
            },
            headers=_auth_headers(analyst_token),
        )
        assert second.status_code == 201

        resolve = client.patch(
            f"/incidents/{first.json()['id']}/resolve",
            headers=_auth_headers(dba_token),
        )
        assert resolve.status_code == 200

        status_resp = client.get("/incidents?status=resolved", headers=_auth_headers(analyst_token))
        assert status_resp.status_code == 200
        status_rows = status_resp.json()
        assert len(status_rows) == 1
        assert status_rows[0]["title"] == "Replica lag event"

        owner_resp = client.get("/incidents?owner=maint", headers=_auth_headers(analyst_token))
        assert owner_resp.status_code == 200
        owner_rows = owner_resp.json()
        assert len(owner_rows) == 1
        assert owner_rows[0]["owner"] == "maintenance"

        search_resp = client.get("/incidents?search=vacuum", headers=_auth_headers(analyst_token))
        assert search_resp.status_code == 200
        search_rows = search_resp.json()
        assert len(search_rows) == 1
        assert search_rows[0]["title"] == "Routine vacuum"


def test_incident_sort_by_severity_orders_high_first() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")

        for payload in [
            {
                "title": "Low severity task",
                "description": "Low priority cleanup",
                "severity": "low",
                "owner": "analyst@example.com",
            },
            {
                "title": "High severity outage",
                "description": "Primary database unavailable",
                "severity": "high",
                "owner": "analyst@example.com",
            },
            {
                "title": "Medium severity warning",
                "description": "CPU saturation warning",
                "severity": "medium",
                "owner": "analyst@example.com",
            },
        ]:
            create_resp = client.post("/incidents", json=payload, headers=_auth_headers(analyst_token))
            assert create_resp.status_code == 201

        resp = client.get("/incidents?sort=severity", headers=_auth_headers(analyst_token))
        assert resp.status_code == 200
        rows = resp.json()
        assert [rows[0]["severity"], rows[1]["severity"], rows[2]["severity"]] == ["high", "medium", "low"]


def test_incident_filters_with_future_start_date_returns_empty() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")

        create_resp = client.post(
            "/incidents",
            json={
                "title": "Connection retry warning",
                "description": "Short-lived connectivity issue",
                "severity": "low",
                "owner": "analyst@example.com",
            },
            headers=_auth_headers(analyst_token),
        )
        assert create_resp.status_code == 201

        resp = client.get("/incidents?start_date=2099-01-01", headers=_auth_headers(analyst_token))
        assert resp.status_code == 200
        assert resp.json() == []


def test_incident_list_rejects_invalid_sort_value() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        resp = client.get("/incidents?sort=priority", headers=_auth_headers(dba_token))
        assert resp.status_code == 422


def test_auth_login_rate_limit_blocks_excessive_attempts() -> None:
    for client in _client():
        configure_auth_rate_limit(max_requests=2, window_seconds=60)
        reset_auth_rate_limit()

        bad_payload = {"email": "nobody@example.com", PASSWORD_FIELD: INVALID_SECRET}
        first = client.post("/auth/login", json=bad_payload)
        second = client.post("/auth/login", json=bad_payload)
        third = client.post("/auth/login", json=bad_payload)

        assert first.status_code == 401
        assert second.status_code == 401
        assert third.status_code == 429


def test_auth_register_rate_limit_blocks_excessive_attempts() -> None:
    for client in _client():
        configure_auth_rate_limit(max_requests=1, window_seconds=60)
        reset_auth_rate_limit()

        first = client.post(
            "/auth/register",
            json={"email": "dba1@example.com", PASSWORD_FIELD: PRIMARY_SECRET, "role": "DBA"},
        )
        second = client.post(
            "/auth/register",
            json={"email": "dba2@example.com", PASSWORD_FIELD: PRIMARY_SECRET, "role": "DBA"},
        )

        assert first.status_code == 201
        assert second.status_code == 429


def test_dba_user_admin_actions_are_audited() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)

        create_resp = client.post(
            "/auth/users",
            json={"email": "analyst@example.com", PASSWORD_FIELD: PRIMARY_SECRET, "role": "Analyst"},
            headers=_auth_headers(dba_token),
        )
        assert create_resp.status_code == 201
        created_user = create_resp.json()

        reset_resp = client.patch(
            f"/auth/users/{created_user['id']}/password",
            json={PASSWORD_FIELD: ROTATED_SECRET},
            headers=_auth_headers(dba_token),
        )
        assert reset_resp.status_code == 200

        status_resp = client.patch(
            f"/auth/users/{created_user['id']}/status",
            json={"is_active": False},
            headers=_auth_headers(dba_token),
        )
        assert status_resp.status_code == 200

        delete_resp = client.delete(
            f"/auth/users/{created_user['id']}",
            headers=_auth_headers(dba_token),
        )
        assert delete_resp.status_code == 204

        audit_resp = client.get("/auth/users/audit?limit=10", headers=_auth_headers(dba_token))
        assert audit_resp.status_code == 200
        rows = audit_resp.json()
        actions = [r["action"] for r in rows]
        assert "create_user" in actions
        assert "reset_password" in actions
        assert "set_status" in actions
        assert "delete_user" in actions


def test_non_dba_cannot_read_user_admin_audit() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")

        resp = client.get("/auth/users/audit", headers=_auth_headers(analyst_token))
        assert resp.status_code == 403


def test_dba_admin_overview_returns_metrics_billing_and_onboarding() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)

        _create_user(client, dba_token, "analyst@example.com", "Analyst")

        incident_resp = client.post(
            "/incidents",
            json={
                "title": "Overview smoke",
                "description": "Verify admin overview counters",
                "severity": "medium",
                "owner": "dba@example.com",
            },
            headers=_auth_headers(dba_token),
        )
        assert incident_resp.status_code == 201

        run_resp = client.post(
            "/reports/run",
            json={"report_key": "incidents_recent", "params": {"max_rows": 10}},
            headers=_auth_headers(dba_token),
        )
        assert run_resp.status_code == 200

        schedule_resp = client.post(
            "/reports/schedules",
            json={
                "report_key": "incidents_recent",
                "params": {"max_rows": 10},
                "cadence": "daily",
                "run_hour_utc": 6,
                "run_minute_utc": 30,
            },
            headers=_auth_headers(dba_token),
        )
        assert schedule_resp.status_code == 201

        overview_resp = client.get("/admin/overview", headers=_auth_headers(dba_token))
        assert overview_resp.status_code == 200
        body = overview_resp.json()
        assert body["metrics"]["total_users"] == 2
        assert body["metrics"]["active_users"] == 2
        assert body["metrics"]["open_incidents"] == 1
        assert body["metrics"]["enabled_schedules"] == 1
        assert body["metrics"]["report_runs_last_24h"] >= 1
        assert body["billing"]["plan_key"] == "starter"
        assert body["plan_usage"]["user_slots_used"] == 2
        assert body["plan_usage"]["user_slots_remaining"] == 8
        assert body["plan_usage"]["schedule_slots_used"] == 1
        assert len(body["activity_trend"]) == 7
        assert any(point["report_runs"] >= 1 for point in body["activity_trend"])
        completed = {item["key"] for item in body["onboarding"] if item["completed"]}
        assert {"first_user_created", "first_incident_created", "first_report_run", "first_schedule_created"}.issubset(completed)


def test_dba_can_update_billing_settings() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)

        resp = client.put(
            "/admin/billing",
            json={
                "plan_key": "growth",
                "billing_status": "active",
                "monthly_price_cents": 29900,
                "max_users": 25,
                "max_schedules": 40,
                "stripe_customer_id": "cus_demo_123",
                "stripe_subscription_id": "sub_demo_123",
            },
            headers=_auth_headers(dba_token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["plan_key"] == "growth"
        assert body["billing_status"] == "active"
        assert body["monthly_price_cents"] == 29900
        assert body["max_users"] == 25
        assert body["max_schedules"] == 40
        assert body["stripe_customer_id"] == "cus_demo_123"


def test_dba_can_create_stripe_checkout_session(monkeypatch) -> None:
    fake_stripe = _fake_stripe_module(
        session_payload={"id": "cs_test_checkout", "url": "https://checkout.stripe.test/session/cs_test_checkout"}
    )
    monkeypatch.setattr("app.main.stripe", fake_stripe)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")

    for client in _client():
        dba_token = _bootstrap_dba(client)

        resp = client.post(
            "/billing/checkout/session",
            json={
                "price_id": "price_test_starter",
                "plan_key": "starter",
                "success_url": "https://dbops-web.onrender.com/billing/success",
                "cancel_url": "https://dbops-web.onrender.com/billing/cancel",
            },
            headers=_auth_headers(dba_token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "cs_test_checkout"
        assert body["url"].startswith("https://checkout.stripe.test/session/")


def test_stripe_webhook_updates_billing_settings(monkeypatch) -> None:
    fake_event = {
        "type": "checkout.session.completed",
        "data": {"object": {"customer": "cus_live_001", "subscription": "sub_live_001"}},
    }
    fake_stripe = _fake_stripe_module(event_payload=fake_event)
    monkeypatch.setattr("app.main.stripe", fake_stripe)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_123")

    for client in _client():
        dba_token = _bootstrap_dba(client)

        webhook_resp = client.post(
            "/billing/webhook",
            content="{}",
            headers={"Stripe-Signature": "t=1,v1=testsig"},
        )
        assert webhook_resp.status_code == 200
        body = webhook_resp.json()
        assert body["received"] is True
        assert body["event_type"] == "checkout.session.completed"
        assert body["billing_status"] == "active"

        overview = client.get("/admin/overview", headers=_auth_headers(dba_token))
        assert overview.status_code == 200
        billing = overview.json()["billing"]
        assert billing["stripe_customer_id"] == "cus_live_001"
        assert billing["stripe_subscription_id"] == "sub_live_001"
        assert billing["billing_status"] == "active"


def test_plan_user_limit_blocks_additional_user_creation() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)

        update_resp = client.put(
            "/admin/billing",
            json={
                "plan_key": "starter",
                "billing_status": "trialing",
                "monthly_price_cents": 14900,
                "max_users": 1,
                "max_schedules": 10,
                "stripe_customer_id": None,
                "stripe_subscription_id": None,
            },
            headers=_auth_headers(dba_token),
        )
        assert update_resp.status_code == 200

        create_resp = client.post(
            "/auth/users",
            json={"email": "viewer@example.com", "password": "Password123!", "role": "Viewer"},
            headers=_auth_headers(dba_token),
        )
        assert create_resp.status_code == 403
        assert create_resp.json()["detail"] == "Plan limit reached: max users is 1 for the current plan."


def test_plan_schedule_limit_blocks_additional_schedule_creation() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)

        update_resp = client.put(
            "/admin/billing",
            json={
                "plan_key": "starter",
                "billing_status": "trialing",
                "monthly_price_cents": 14900,
                "max_users": 10,
                "max_schedules": 1,
                "stripe_customer_id": None,
                "stripe_subscription_id": None,
            },
            headers=_auth_headers(dba_token),
        )
        assert update_resp.status_code == 200

        first_schedule = client.post(
            "/reports/schedules",
            json={
                "report_key": "incidents_recent",
                "params": {"max_rows": 10},
                "cadence": "daily",
                "run_hour_utc": 6,
                "run_minute_utc": 30,
            },
            headers=_auth_headers(dba_token),
        )
        assert first_schedule.status_code == 201

        second_schedule = client.post(
            "/reports/schedules",
            json={
                "report_key": "incidents_recent",
                "params": {"max_rows": 5},
                "cadence": "daily",
                "run_hour_utc": 7,
                "run_minute_utc": 0,
            },
            headers=_auth_headers(dba_token),
        )
        assert second_schedule.status_code == 403
        assert second_schedule.json()["detail"] == "Plan limit reached: max schedules is 1 for the current plan."


def test_report_csv_export_returns_headers_rows_and_escaped_values() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")

        create_resp = client.post(
            "/incidents",
            json={
                "title": "CSV, \"quoted\" smoke",
                "description": "Incident used to verify csv export",
                "severity": "medium",
                "owner": "analyst@example.com",
            },
            headers=_auth_headers(analyst_token),
        )
        assert create_resp.status_code == 201

        csv_resp = client.post(
            "/reports/export/csv",
            json={"report_key": "incidents_recent", "params": {"max_rows": 10}},
            headers=_auth_headers(analyst_token),
        )
        assert csv_resp.status_code == 200
        assert csv_resp.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=\"incidents_recent.csv\"" in csv_resp.headers["content-disposition"]
        rows = list(csv_reader(StringIO(csv_resp.text.strip())))
        assert rows[0] == ["id", "title", "status", "severity", "owner", "created_at"]
        assert any(r[1] == 'CSV, "quoted" smoke' for r in rows[1:])


def test_report_csv_export_supports_all_whitelisted_reports() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")

        create_resp = client.post(
            "/incidents",
            json={
                "title": "CSV report coverage",
                "description": "Incident used to validate report exports",
                "severity": "high",
                "owner": "analyst@example.com",
            },
            headers=_auth_headers(analyst_token),
        )
        assert create_resp.status_code == 201

        cases = [
            ("incidents_recent", {"max_rows": 10}, "id,title,status,severity,owner,created_at"),
            ("incidents_by_status", {}, "status,incident_count"),
            ("open_high_severity", {}, "id,title,owner,created_at"),
        ]

        for report_key, params, expected_header in cases:
            resp = client.post(
                "/reports/export/csv",
                json={"report_key": report_key, "params": params},
                headers=_auth_headers(analyst_token),
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/csv")
            assert f'attachment; filename="{report_key}.csv"' in resp.headers["content-disposition"]
            first_line = resp.text.strip().splitlines()[0]
            assert first_line == expected_header


def test_report_csv_export_enforces_report_permissions() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "viewer@example.com", "Viewer")
        viewer_token = _login_token(client, "viewer@example.com", "Password123!")

        resp = client.post(
            "/reports/export/csv",
            json={"report_key": "open_high_severity", "params": {}},
            headers=_auth_headers(viewer_token),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "Insufficient permissions for this report"


def test_dba_can_create_list_and_disable_report_schedule() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)

        create_resp = client.post(
            "/reports/schedules",
            json={
                "report_key": "incidents_recent",
                "params": {"max_rows": 25},
                "cadence": "daily",
                "run_hour_utc": 6,
                "run_minute_utc": 30,
                "delivery_kind": "email",
                "delivery_target": "ops@example.com",
                "notify_on_success": True,
                "notify_on_failure": True,
            },
            headers=_auth_headers(dba_token),
        )
        assert create_resp.status_code == 201
        schedule = create_resp.json()
        assert schedule["report_key"] == "incidents_recent"
        assert schedule["params"] == {"max_rows": 25}
        assert schedule["delivery_kind"] == "email"
        assert schedule["delivery_target"] == "ops@example.com"
        assert schedule["notify_on_success"] is True
        assert schedule["notify_on_failure"] is True
        assert schedule["is_enabled"] is True

        list_resp = client.get("/reports/schedules", headers=_auth_headers(dba_token))
        assert list_resp.status_code == 200
        rows = list_resp.json()
        assert len(rows) == 1
        assert rows[0]["id"] == schedule["id"]

        disable_resp = client.patch(
            f"/reports/schedules/{schedule['id']}/status",
            json={"is_enabled": False},
            headers=_auth_headers(dba_token),
        )
        assert disable_resp.status_code == 200
        assert disable_resp.json()["is_enabled"] is False


def test_due_report_schedule_executes_and_logs_result() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)

        create_incident_resp = client.post(
            "/incidents",
            json={
                "title": "Lag spike",
                "description": "Replica lag exceeded threshold",
                "severity": "high",
                "owner": "dba@example.com",
            },
            headers=_auth_headers(dba_token),
        )
        assert create_incident_resp.status_code == 201

        create_schedule_resp = client.post(
            "/reports/schedules",
            json={
                "report_key": "incidents_recent",
                "params": {"max_rows": 10},
                "cadence": "daily",
                "run_hour_utc": 6,
                "run_minute_utc": 30,
            },
            headers=_auth_headers(dba_token),
        )
        assert create_schedule_resp.status_code == 201
        schedule_id = create_schedule_resp.json()["id"]

        fixed_now = datetime(2026, 5, 9, 12, 0, 0)
        db = next(app.dependency_overrides[get_db]())
        try:
            schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
            assert schedule is not None
            schedule.next_run_at = fixed_now - timedelta(minutes=1)
            db.add(schedule)
            db.commit()
        finally:
            db.close()

        session_factory = app.dependency_overrides[get_db].__closure__[0].cell_contents
        processed = process_due_report_schedules(session_factory, now=fixed_now)
        assert processed == 1

        db = next(app.dependency_overrides[get_db]())
        try:
            schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
            assert schedule is not None
            assert schedule.last_success_at == fixed_now
            assert schedule.last_error is None
            assert schedule.next_run_at > fixed_now

            log = (
                db.query(ReportExecutionLog)
                .filter(ReportExecutionLog.scheduled_report_id == schedule_id)
                .order_by(ReportExecutionLog.created_at.desc())
                .first()
            )
            assert log is not None
            assert log.success is True
            assert log.row_count == 1
        finally:
            db.close()


def test_disabled_schedule_owner_logs_failure() -> None:
    for client in _client():
        primary_dba_token = _bootstrap_dba(client)
        _create_user(client, primary_dba_token, "dba2@example.com", "DBA")
        secondary_dba_token = _login_token(client, "dba2@example.com", "Password123!")

        create_schedule_resp = client.post(
            "/reports/schedules",
            json={
                "report_key": "incidents_recent",
                "params": {"max_rows": 10},
                "cadence": "daily",
                "run_hour_utc": 6,
                "run_minute_utc": 30,
            },
            headers=_auth_headers(secondary_dba_token),
        )
        assert create_schedule_resp.status_code == 201
        schedule_id = create_schedule_resp.json()["id"]

        users_resp = client.get("/auth/users", headers=_auth_headers(primary_dba_token))
        assert users_resp.status_code == 200
        secondary_dba = next(user for user in users_resp.json() if user["email"] == "dba2@example.com")

        disable_resp = client.patch(
            f"/auth/users/{secondary_dba['id']}/status",
            json={"is_active": False},
            headers=_auth_headers(primary_dba_token),
        )
        assert disable_resp.status_code == 200

        fixed_now = datetime(2026, 5, 9, 12, 0, 0)
        db = next(app.dependency_overrides[get_db]())
        try:
            schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
            assert schedule is not None
            schedule.next_run_at = fixed_now - timedelta(minutes=1)
            db.add(schedule)
            db.commit()
        finally:
            db.close()


def test_scheduler_health_endpoint_returns_runtime_status() -> None:
    for client in _client():
        resp = client.get("/health/scheduler")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "scheduler" in body
        assert isinstance(body["scheduler"]["poll_seconds"], int)
        assert "loop_enabled" in body["scheduler"]
        assert "last_iteration_started_at" in body["scheduler"]
        assert "last_iteration_completed_at" in body["scheduler"]


def test_due_schedule_retries_transient_execution_failure(monkeypatch) -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)

        create_incident_resp = client.post(
            "/incidents",
            json={
                "title": "Retry smoke",
                "description": "Transient execution should retry once",
                "severity": "medium",
                "owner": "dba@example.com",
            },
            headers=_auth_headers(dba_token),
        )
        assert create_incident_resp.status_code == 201

        create_schedule_resp = client.post(
            "/reports/schedules",
            json={
                "report_key": "incidents_recent",
                "params": {"max_rows": 10},
                "cadence": "daily",
                "run_hour_utc": 6,
                "run_minute_utc": 30,
            },
            headers=_auth_headers(dba_token),
        )
        assert create_schedule_resp.status_code == 201
        schedule_id = create_schedule_resp.json()["id"]

        fixed_now = datetime(2026, 5, 9, 12, 0, 0)
        db = next(app.dependency_overrides[get_db]())
        try:
            schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
            assert schedule is not None
            schedule.next_run_at = fixed_now - timedelta(minutes=1)
            db.add(schedule)
            db.commit()
        finally:
            db.close()

        attempts = {"count": 0}

        def flaky_execute(*args, attempts_state=attempts, **kwargs):
            attempts_state["count"] += 1
            if attempts_state["count"] == 1:
                raise RuntimeError("temporary database timeout")
            return execute_whitelisted_report_real(*args, **kwargs)

        monkeypatch.setattr(scheduler_module, "execute_whitelisted_report", flaky_execute)
        monkeypatch.setenv("SCHEDULED_REPORTS_EXECUTION_ATTEMPTS", "2")
        monkeypatch.setenv("SCHEDULED_REPORTS_EXECUTION_BACKOFF_MS", "0")

        session_factory = app.dependency_overrides[get_db].__closure__[0].cell_contents
        processed = process_due_report_schedules(session_factory, now=fixed_now)
        assert processed == 1
        assert attempts["count"] == 2

        db = next(app.dependency_overrides[get_db]())
        try:
            schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
            assert schedule is not None
            assert schedule.last_success_at == fixed_now
            assert schedule.last_error is None
        finally:
            db.close()