from app.billing_plans import (
    ENTERPRISE_PLAN_LIMIT,
    PLAN_CATALOG,
    PRO_PLAN_LIMIT,
    apply_plan_catalog_to_settings,
    is_plan_downgrade,
    normalize_plan_key,
    plan_key_for_stripe_price_id,
    pending_plan_key_from_stripe_object,
    resolve_plan_key_from_stripe_object,
)
from app.models import BillingSettings


def test_normalize_plan_key_is_case_insensitive() -> None:
    assert normalize_plan_key("Pro") == "pro"
    assert normalize_plan_key("unknown") is None


def test_starter_plan_price() -> None:
    assert PLAN_CATALOG["starter"].monthly_price_cents == 7900


def test_billing_settings_column_defaults_match_starter_catalog() -> None:
    """ORM defaults on insert must match PLAN_CATALOG starter (buyer-facing DB consistency)."""
    starter = PLAN_CATALOG["starter"]
    columns = BillingSettings.__table__.columns
    assert columns["plan_key"].default.arg == starter.plan_key
    assert columns["monthly_price_cents"].default.arg == starter.monthly_price_cents
    assert columns["max_users"].default.arg == starter.max_users
    assert columns["max_schedules"].default.arg == starter.max_schedules


def test_pro_plan_uses_pro_tier_limits() -> None:
    assert PLAN_CATALOG["pro"].max_users == PRO_PLAN_LIMIT
    assert PLAN_CATALOG["pro"].max_schedules == PRO_PLAN_LIMIT
    assert PLAN_CATALOG["enterprise"].max_users == ENTERPRISE_PLAN_LIMIT


def test_apply_plan_catalog_to_settings_updates_pro_limits() -> None:
    settings = BillingSettings(id=1, plan_key="starter", max_users=10, max_schedules=10, monthly_price_cents=7900)
    assert apply_plan_catalog_to_settings(settings, "pro") is True
    assert settings.plan_key == "pro"
    assert settings.max_users == PRO_PLAN_LIMIT
    assert settings.max_schedules == PRO_PLAN_LIMIT
    assert settings.monthly_price_cents == 14900


def test_resolve_plan_key_from_checkout_metadata() -> None:
    event_object = {"metadata": {"plan_key": "pro"}}
    assert resolve_plan_key_from_stripe_object(event_object) == "pro"


def test_resolve_plan_key_from_subscription_price_id(monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_PRICE_ID_PRO", "price_pro_live")
    event_object = {
        "items": {
            "data": [
                {"price": {"id": "price_pro_live"}},
            ],
        },
    }
    assert resolve_plan_key_from_stripe_object(event_object) == "pro"
    assert plan_key_for_stripe_price_id("price_pro_live") == "pro"


def test_is_plan_downgrade_requires_lower_tier() -> None:
    assert is_plan_downgrade("pro", "starter") is True
    assert is_plan_downgrade("enterprise", "pro") is True
    assert is_plan_downgrade("starter", "pro") is False
    assert is_plan_downgrade("pro", "pro") is False


def test_pending_plan_key_from_subscription_metadata() -> None:
    event_object = {"metadata": {"plan_key": "pro", "pending_plan_key": "starter"}}
    assert pending_plan_key_from_stripe_object(event_object) == "starter"
