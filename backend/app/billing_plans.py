"""Plan catalog and Stripe → billing limit mapping."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import BillingSettings

# Pro gets high capacity; Enterprise gets schema max. Starter stays at 10.
PRO_PLAN_LIMIT = 5_000
ENTERPRISE_PLAN_LIMIT = 10_000


@dataclass(frozen=True)
class PlanDefinition:
    plan_key: str
    monthly_price_cents: int
    max_users: int
    max_schedules: int


PLAN_CATALOG: dict[str, PlanDefinition] = {
    "starter": PlanDefinition("starter", 4900, 10, 10),
    "pro": PlanDefinition("pro", 14900, PRO_PLAN_LIMIT, PRO_PLAN_LIMIT),
    "enterprise": PlanDefinition("enterprise", 39900, ENTERPRISE_PLAN_LIMIT, ENTERPRISE_PLAN_LIMIT),
}

PLAN_TIER_ORDER: dict[str, int] = {"starter": 0, "pro": 1, "enterprise": 2}

STRIPE_PRICE_ENV_BY_PLAN: dict[str, str] = {
    "starter": "STRIPE_PRICE_ID_STARTER",
    "pro": "STRIPE_PRICE_ID_PRO",
    "enterprise": "STRIPE_PRICE_ID_ENTERPRISE",
}

ACTIVE_SUBSCRIPTION_STATUSES = frozenset({"active", "trialing", "past_due"})


def normalize_plan_key(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower()
    return key if key in PLAN_CATALOG else None


def plan_key_for_stripe_price_id(price_id: str | None) -> str | None:
    if not price_id:
        return None
    normalized = price_id.strip()
    env_mappings = (
        ("STRIPE_PRICE_ID_STARTER", "starter"),
        ("STRIPE_PRICE_ID_PRO", "pro"),
        ("STRIPE_PRICE_ID_ENTERPRISE", "enterprise"),
    )
    for env_name, plan_key in env_mappings:
        configured = os.getenv(env_name, "").strip()
        if configured and configured == normalized:
            return plan_key
    return None


def _stripe_get(value: Any, key: str) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _metadata_plan_key(event_object: Any) -> str | None:
    metadata = _stripe_get(event_object, "metadata")
    if isinstance(metadata, dict):
        return normalize_plan_key(metadata.get("plan_key"))
    return None


def _subscription_price_id(event_object: Any) -> str | None:
    items = _stripe_get(event_object, "items")
    rows = _stripe_get(items, "data") if items else None
    if not rows:
        return None
    price = _stripe_get(rows[0], "price")
    if isinstance(price, str):
        return price.strip() or None
    price_id = _stripe_get(price, "id")
    if isinstance(price_id, str) and price_id.strip():
        return price_id.strip()
    return None


def resolve_plan_key_from_stripe_object(event_object: Any) -> str | None:
    from_metadata = _metadata_plan_key(event_object)
    if from_metadata:
        return from_metadata
    return plan_key_for_stripe_price_id(_subscription_price_id(event_object))


def pending_plan_key_from_stripe_object(event_object: Any) -> str | None:
    metadata = _stripe_get(event_object, "metadata")
    if isinstance(metadata, dict):
        return normalize_plan_key(metadata.get("pending_plan_key"))
    return None


def apply_plan_catalog_to_settings(settings: BillingSettings, plan_key: str) -> bool:
    normalized = normalize_plan_key(plan_key)
    if normalized is None:
        return False
    plan = PLAN_CATALOG[normalized]
    settings.plan_key = plan.plan_key
    settings.monthly_price_cents = plan.monthly_price_cents
    settings.max_users = plan.max_users
    settings.max_schedules = plan.max_schedules
    return True


def is_plan_downgrade(from_plan_key: str, to_plan_key: str) -> bool:
    from_plan = normalize_plan_key(from_plan_key)
    to_plan = normalize_plan_key(to_plan_key)
    if from_plan is None or to_plan is None:
        return False
    return PLAN_TIER_ORDER[to_plan] < PLAN_TIER_ORDER[from_plan]


def stripe_price_env_name(plan_key: str) -> str | None:
    normalized = normalize_plan_key(plan_key)
    if normalized is None:
        return None
    return STRIPE_PRICE_ENV_BY_PLAN.get(normalized)
