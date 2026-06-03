"""Render hosting cost vs MRR monitor tests."""

import os
from unittest.mock import patch

from tests.test_auth_rbac import _auth_headers, _bootstrap_dba, _client

from app.render_monitor import check_upgrade_needed, get_mrr_from_db


def test_check_upgrade_needed_below_threshold() -> None:
    with patch.dict(os.environ, {"RENDER_CURRENT_COST": "87", "PROFIT_MULTIPLIER": "3"}, clear=False):
        status = check_upgrade_needed(mrr=200, client_count=4)
    assert status["should_upgrade"] is False
    assert status["upgrade_threshold"] == 261
    assert "Profitable" in status["recommendation"]


def test_check_upgrade_needed_at_threshold() -> None:
    with patch.dict(os.environ, {"RENDER_CURRENT_COST": "87", "PROFIT_MULTIPLIER": "3"}, clear=False):
        status = check_upgrade_needed(mrr=261, client_count=6)
    assert status["should_upgrade"] is True
    assert status["next_tier"] == "Growth"
    assert "UPGRADE NOW" in status["recommendation"]


def test_get_mrr_from_db_uses_billing_settings() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.db import Base
    from app.models import BillingSettings, User

    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(
        BillingSettings(
            id=1,
            plan_key="pro",
            billing_status="active",
            monthly_price_cents=14900,
            max_users=5000,
            max_schedules=5000,
        )
    )
    session.add(User(email="a@example.com", hashed_password="x", role="DBA", is_active=True))
    session.commit()

    mrr, clients = get_mrr_from_db(session)
    assert mrr == 149.0
    assert clients == 1


def test_render_monitor_endpoint_dba_only() -> None:
    with patch.dict(
        os.environ,
        {"RENDER_CURRENT_COST": "87", "PROFIT_MULTIPLIER": "3", "MONITOR_MRR_USD": "261"},
        clear=False,
    ):
        for client in _client():
            dba_token = _bootstrap_dba(client)
            resp = client.get("/admin/render-monitor", headers=_auth_headers(dba_token))
            assert resp.status_code == 200
            data = resp.json()
            assert data["mrr"] == 261.0
            assert data["should_upgrade"] is True
            assert data["alert_sent"] is False

            forbidden = client.get("/admin/render-monitor")
            assert forbidden.status_code == 401


def test_render_monitor_sends_alert_once(monkeypatch) -> None:
    sent: list[dict] = []

    def fake_send(status):
        sent.append(status)
        return True

    monkeypatch.setattr("app.render_monitor.send_upgrade_alert", fake_send)

    with patch.dict(
        os.environ,
        {
            "RENDER_CURRENT_COST": "87",
            "PROFIT_MULTIPLIER": "3",
            "MONITOR_MRR_USD": "300",
            "SMTP_HOST": "smtp.example.com",
        },
        clear=False,
    ):
        for client in _client():
            dba_token = _bootstrap_dba(client)
            first = client.get(
                "/admin/render-monitor?send_alert=true",
                headers=_auth_headers(dba_token),
            )
            assert first.status_code == 200
            assert first.json()["alert_sent"] is True
            assert len(sent) == 1

            second = client.get(
                "/admin/render-monitor?send_alert=true",
                headers=_auth_headers(dba_token),
            )
            assert second.status_code == 200
            assert second.json()["alert_sent"] is False
            assert second.json()["alert_skipped_reason"] == "Alert already sent for this Render cost tier"
            assert len(sent) == 1
