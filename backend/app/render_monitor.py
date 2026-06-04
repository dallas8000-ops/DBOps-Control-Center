"""Render hosting cost vs MRR monitor — alerts when revenue exceeds profit threshold."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from .billing_plans import PLAN_CATALOG
from .models import BillingSettings, OnboardingEvent, User
from .smtp_notify import send_smtp_text_email, smtp_configured

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

RENDER_TIERS: list[dict[str, Any]] = [
    {"name": "Current", "cost": 87, "max_clients": 4, "upgrade_at_revenue": 261},
    {"name": "Growth", "cost": 150, "max_clients": 10, "upgrade_at_revenue": 450},
    {"name": "Scale", "cost": 300, "max_clients": 30, "upgrade_at_revenue": 900},
    {"name": "Enterprise", "cost": 500, "max_clients": 100, "upgrade_at_revenue": 1500},
]

ACTIVE_BILLING_STATUSES = frozenset({"active", "trialing", "past_due"})
STRIPE_FEE_RATE = 0.029


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def profit_multiplier() -> float:
    return _env_float("PROFIT_MULTIPLIER", 3.0)


def render_current_cost() -> float:
    return _env_float("RENDER_CURRENT_COST", 87.0)


def alert_email() -> str:
    return os.getenv("ALERT_EMAIL", "barney@gilliomfrontlinedigital.com").strip()


def plan_price_usd(plan_key: str) -> float:
    plan = PLAN_CATALOG.get(plan_key.strip().lower())
    if plan is None:
        return 0.0
    return plan.monthly_price_cents / 100.0


def get_mrr_from_db(db: Session) -> tuple[float, int]:
    """
    MRR from billing_settings when subscription is active, with optional overrides
    for operators tracking total Stripe MRR outside the single-tenant billing row.
    """
    override = os.getenv("MONITOR_MRR_USD", "").strip()
    if override:
        mrr = float(override)
    else:
        settings = db.query(BillingSettings).filter(BillingSettings.id == 1).first()
        if settings is not None and settings.billing_status in ACTIVE_BILLING_STATUSES:
            mrr = settings.monthly_price_cents / 100.0
        else:
            mrr = 0.0

    client_override = os.getenv("MONITOR_CLIENT_COUNT", "").strip()
    if client_override:
        client_count = int(client_override)
    else:
        client_count = db.query(User).filter(User.is_active.is_(True)).count()
    return mrr, client_count


def get_current_render_tier() -> dict[str, Any]:
    cost = render_current_cost()
    for tier in RENDER_TIERS:
        if tier["cost"] == cost:
            return tier
    closest = min(RENDER_TIERS, key=lambda t: abs(t["cost"] - cost))
    return closest


def get_next_render_tier() -> dict[str, Any] | None:
    cost = render_current_cost()
    for index, tier in enumerate(RENDER_TIERS):
        if tier["cost"] == cost and index + 1 < len(RENDER_TIERS):
            return RENDER_TIERS[index + 1]
    return None


def _get_recommendation(mrr: float, threshold: float, next_tier: dict[str, Any] | None, net: float) -> str:
    if mrr == 0:
        return "No active subscription revenue yet. Keep marketing!"
    if net < 0:
        return f"Still pre-profit. Need ${abs(net):.0f}/mo more revenue to break even after Render and Stripe fees."
    if mrr < threshold:
        remaining = threshold - mrr
        return (
            f"Profitable! Need ${remaining:.0f}/mo more revenue before upgrading Render "
            f"(at {profit_multiplier():.0f}x rule)."
        )
    if next_tier:
        return (
            f"UPGRADE NOW — Revenue (${mrr:.0f}/mo) is {mrr / threshold:.1f}x your Render cost. "
            f"Upgrade to Render {next_tier['name']} (${next_tier['cost']}/mo) for better reliability."
        )
    return "You're on the max Render tier. Consider moving to dedicated infrastructure."


def check_upgrade_needed(mrr: float, client_count: int) -> dict[str, Any]:
    current_tier = get_current_render_tier()
    next_tier = get_next_render_tier()
    render_cost = render_current_cost()
    upgrade_threshold = render_cost * profit_multiplier()
    stripe_fees = mrr * STRIPE_FEE_RATE
    net_profit = mrr - render_cost
    real_net = net_profit - stripe_fees
    profit_margin = (net_profit / mrr * 100) if mrr > 0 else 0.0
    starter_price = plan_price_usd("starter") or 79.0
    clients_to_breakeven = max(0, int(-(-int(render_cost) // int(starter_price))))

    should_upgrade = mrr >= upgrade_threshold and next_tier is not None

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "mrr": round(mrr, 2),
        "client_count": client_count,
        "net_profit": round(real_net, 2),
        "profit_margin_pct": round(profit_margin, 1),
        "stripe_fees": round(stripe_fees, 2),
        "render_cost": render_cost,
        "upgrade_threshold": round(upgrade_threshold, 2),
        "profit_multiplier": profit_multiplier(),
        "should_upgrade": should_upgrade,
        "clients_to_breakeven": clients_to_breakeven,
        "current_tier": current_tier["name"],
        "next_tier": next_tier["name"] if next_tier else "Already on max tier",
        "next_tier_cost": next_tier["cost"] if next_tier else None,
        "recommendation": _get_recommendation(mrr, upgrade_threshold, next_tier, real_net),
        "alert_email": alert_email(),
        "smtp_configured": smtp_configured(),
    }


def _alert_event_key(render_cost: float) -> str:
    return f"render_upgrade_alert_{int(render_cost)}"


def alert_already_sent(db: Session, render_cost: float) -> bool:
    return (
        db.query(OnboardingEvent)
        .filter(OnboardingEvent.event_key == _alert_event_key(render_cost))
        .first()
        is not None
    )


def record_alert_sent(db: Session, *, actor_user_id: int | None, status: dict[str, Any]) -> None:
    db.add(
        OnboardingEvent(
            event_key=_alert_event_key(render_current_cost()),
            actor_user_id=actor_user_id,
            details_json=str(
                {
                    "mrr": status["mrr"],
                    "next_tier": status["next_tier"],
                    "render_cost": status["render_cost"],
                }
            ),
        )
    )


def send_upgrade_alert(status: dict[str, Any]) -> bool:
    if not smtp_configured():
        logger.info("render_monitor: SMTP not configured — skipping email alert")
        return False

    subject = f"Time to upgrade Render — MRR ${status['mrr']}/mo"
    body = f"""Hi Barney,

Your DBOps MRR has hit the upgrade threshold.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Active users/clients: {status['client_count']}
Monthly revenue:      ${status['mrr']}
Render cost:          ${status['render_cost']}
Stripe fees (est.):   ${status['stripe_fees']}
Net profit (est.):    ${status['net_profit']}
Profit margin:        {status['profit_margin_pct']}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Recommendation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{status['recommendation']}

Current Render tier:  {status['current_tier']} (${status['render_cost']}/mo)
Upgrade to:           {status['next_tier']} (${status['next_tier_cost']}/mo)

Action: dashboard.render.com → Billing → Upgrade Plan

— DBOps Render Monitor
{status['timestamp']} UTC
""".strip()

    try:
        send_smtp_text_email(to_addr=alert_email(), subject=subject, body=body)
        logger.info("render_monitor: alert sent to %s", alert_email())
        return True
    except Exception as exc:
        logger.exception("render_monitor: email failed: %s", exc)
        return False


def evaluate_render_monitor(db: Session, *, actor_user_id: int | None = None, send_alert: bool = False) -> dict[str, Any]:
    mrr, client_count = get_mrr_from_db(db)
    status = check_upgrade_needed(mrr, client_count)
    status["alert_sent"] = False
    status["alert_skipped_reason"] = None

    if status["should_upgrade"] and send_alert:
        if alert_already_sent(db, render_current_cost()):
            status["alert_skipped_reason"] = "Alert already sent for this Render cost tier"
        else:
            if send_upgrade_alert(status):
                record_alert_sent(db, actor_user_id=actor_user_id, status=status)
                db.commit()
                status["alert_sent"] = True
            else:
                status["alert_skipped_reason"] = "SMTP not configured or send failed"
    return status


def scheduled_render_monitor_check(db: Session) -> dict[str, Any] | None:
    if os.getenv("RENDER_MONITOR_DISABLE", "").lower() in {"1", "true", "yes"}:
        return None
    return evaluate_render_monitor(db, actor_user_id=None, send_alert=True)
