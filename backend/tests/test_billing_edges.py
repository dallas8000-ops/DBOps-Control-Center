"""Stripe billing webhook edge cases and downgrade lifecycle tests."""

from types import SimpleNamespace

from tests.test_auth_rbac import (
    _auth_headers,
    _bootstrap_dba,
    _client,
)


def _fake_stripe_with_subscription_retrieve(subscription: dict):
    event_holder: dict = {}

    def construct_event(**kwargs):
        return event_holder["event"]

    def set_event(event: dict) -> None:
        event_holder["event"] = event

    fake = SimpleNamespace(
        api_key=None,
        Subscription=SimpleNamespace(retrieve=lambda sub_id: subscription),
        Webhook=SimpleNamespace(construct_event=construct_event),
    )
    fake.set_event = set_event
    return fake


def test_stripe_webhook_invoice_paid_applies_pending_downgrade(monkeypatch) -> None:
    subscription = {
        "id": "sub_pro_live",
        "customer": "cus_pro_live",
        "metadata": {"plan_key": "pro", "pending_plan_key": "starter"},
    }
    fake_stripe = _fake_stripe_with_subscription_retrieve(subscription)
    monkeypatch.setattr("app.main.stripe", fake_stripe)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_123")

    fake_event = {
        "type": "invoice.paid",
        "data": {"object": {"subscription": "sub_pro_live", "customer": "cus_pro_live"}},
    }
    fake_stripe.set_event(fake_event)

    for client in _client():
        dba_token = _bootstrap_dba(client)

        seed_resp = client.put(
            "/admin/billing",
            json={
                "plan_key": "pro",
                "billing_status": "active",
                "monthly_price_cents": 14900,
                "max_users": 5000,
                "max_schedules": 5000,
                "stripe_customer_id": "cus_pro_live",
                "stripe_subscription_id": "sub_pro_live",
            },
            headers=_auth_headers(dba_token),
        )
        assert seed_resp.status_code == 200

        webhook_resp = client.post(
            "/billing/webhook",
            content="{}",
            headers={"Stripe-Signature": "t=1,v1=testsig"},
        )
        assert webhook_resp.status_code == 200
        assert webhook_resp.json()["event_type"] == "invoice.paid"

        overview = client.get("/admin/overview", headers=_auth_headers(dba_token))
        billing = overview.json()["billing"]
        assert billing["plan_key"] == "starter"
        assert billing["max_users"] == 10
        assert billing["max_schedules"] == 10


def test_billing_health_lists_invoice_paid_webhook_event(monkeypatch) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    for client in _client():
        resp = client.get("/health/billing")
        assert resp.status_code == 503
        assert "invoice.paid" in resp.json()["required_webhook_events"]
