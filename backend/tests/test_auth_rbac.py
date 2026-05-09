import os
from collections.abc import Generator
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import ReportExecutionLog, ReportSchedule
from app.rate_limit import configure_auth_rate_limit, reset_auth_rate_limit
from app.scheduler import process_due_report_schedules


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login_token(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _bootstrap_dba(client: TestClient) -> str:
    payload = {"email": "dba@example.com", "password": "Password123!", "role": "DBA"}
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    return _login_token(client, payload["email"], payload["password"])


def _create_user(client: TestClient, dba_token: str, email: str, role: str) -> None:
    resp = client.post(
        "/auth/users",
        json={"email": email, "password": "Password123!", "role": role},
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

        bad_payload = {"email": "nobody@example.com", "password": "wrong-pass"}
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
            json={"email": "dba1@example.com", "password": "Password123!", "role": "DBA"},
        )
        second = client.post(
            "/auth/register",
            json={"email": "dba2@example.com", "password": "Password123!", "role": "DBA"},
        )

        assert first.status_code == 201
        assert second.status_code == 429


def test_dba_user_admin_actions_are_audited() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)

        create_resp = client.post(
            "/auth/users",
            json={"email": "analyst@example.com", "password": "Password123!", "role": "Analyst"},
            headers=_auth_headers(dba_token),
        )
        assert create_resp.status_code == 201
        created_user = create_resp.json()

        reset_resp = client.patch(
            f"/auth/users/{created_user['id']}/password",
            json={"password": "AnotherPass123!"},
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


def test_report_csv_export_returns_headers_and_rows() -> None:
    for client in _client():
        dba_token = _bootstrap_dba(client)
        _create_user(client, dba_token, "analyst@example.com", "Analyst")
        analyst_token = _login_token(client, "analyst@example.com", "Password123!")

        create_resp = client.post(
            "/incidents",
            json={
                "title": "CSV export smoke",
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
        lines = csv_resp.text.strip().splitlines()
        assert lines[0] == "id,title,status,severity,owner,created_at"
        assert any("CSV export smoke" in line for line in lines[1:])


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
            },
            headers=_auth_headers(dba_token),
        )
        assert create_resp.status_code == 201
        schedule = create_resp.json()
        assert schedule["report_key"] == "incidents_recent"
        assert schedule["params"] == {"max_rows": 25}
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

        session_factory = app.dependency_overrides[get_db].__closure__[0].cell_contents
        processed = process_due_report_schedules(session_factory, now=fixed_now)
        assert processed == 1

        db = next(app.dependency_overrides[get_db]())
        try:
            schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
            assert schedule is not None
            assert schedule.last_success_at is None
            assert schedule.last_error == "Schedule owner is disabled"

            log = (
                db.query(ReportExecutionLog)
                .filter(ReportExecutionLog.scheduled_report_id == schedule_id)
                .order_by(ReportExecutionLog.created_at.desc())
                .first()
            )
            assert log is not None
            assert log.success is False
            assert log.error_message == "Schedule owner is disabled"
        finally:
            db.close()