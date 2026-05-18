import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager
import csv
import json
import logging
import os
import uuid
from csv import DictWriter
from datetime import UTC, date, datetime, time, timedelta
from io import StringIO
from typing import Annotated, Any, TypeAlias

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import case, or_, text
from sqlalchemy.orm import Session

try:
    import stripe
except ImportError:  # pragma: no cover - surfaced via HTTP 503 when feature is used.
    stripe = None

from jose import JWTError
from .auth_utils import create_access_token, hash_password, verify_password
from . import oidc_verify as _oidc
from .db import engine, get_db
from .deps import get_current_user, require_roles
from .models import (
    BillingSettings,
    Incident,
    IncidentHistory,
    OnboardingEvent,
    ReportExecutionLog,
    ReportSchedule,
    User,
    UserAdminAuditLog,
)
from .report_catalog import REPORTS
from .rate_limit import check_api_rate_limit, check_auth_rate_limit
from .report_runner import execute_whitelisted_report, prepare_report_request
from .request_context import reset_request_id, set_request_id
from .scheduler import compute_next_run_at, get_scheduler_runtime_status, run_scheduler_loop
from .schemas import (
    ActivityTrendPointRead,
    AdminMetricsRead,
    AdminOverviewRead,
    BillingCheckoutSessionCreate,
    BillingCheckoutSessionRead,
    BillingSettingsRead,
    BillingSettingsUpdate,
    IncidentCreate,
    IncidentBulkActionRequest,
    IncidentBulkActionResult,
    IncidentHistoryRead,
    IncidentRead,
    IncidentUpdate,
    LoginRequest,
    OidcCallbackRequest,
    ReportCatalogEntry,
    ReportExecuteRequest,
    ReportExecuteResponse,
    ReportParamSpec,
    ReportRunRead,
    ReportScheduleCreate,
    ReportScheduleRead,
    ReportScheduleStatusUpdate,
    StripeWebhookEventRead,
    Token,
    OnboardingItemRead,
    PlanUsageRead,
    UserAdminAuditRead,
    UserCreate,
    UserPasswordReset,
    UserRead,
    UserStatusUpdate,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop_event = asyncio.Event()
    task = None
    if os.getenv("SCHEDULED_REPORTS_DISABLE_LOOP", "").lower() not in ("1", "true", "yes"):
        task = asyncio.create_task(run_scheduler_loop(stop_event))
    try:
        yield
    finally:
        if task is not None:
            stop_event.set()
            await task


app = FastAPI(title="DBOps Control Center API", version="0.4.2", lifespan=lifespan)

ACCESS_LOG = logging.getLogger("dbops.access")

AUTH_RATE_LIMIT_DETAIL = "Too many auth requests. Please try again shortly."
API_RATE_LIMIT_DETAIL = "Too many requests. Please try again shortly."
API_RATE_LIMIT_DESCRIPTION = "API rate limit exceeded"
ACCOUNT_DISABLED_DETAIL = "Your account is disabled. Contact a DBA."
USER_NOT_FOUND_DETAIL = "User not found"
INCIDENT_NOT_FOUND_DETAIL = "Incident not found"
REPORT_PERMISSION_DETAIL = "Insufficient permissions for this report"
UNKNOWN_REPORT_PREFIX = "Unknown report:"

ERROR_RESPONSES_AUTH_LOGIN = {
    401: {"description": "Incorrect credentials"},
    403: {"description": "Account disabled"},
    429: {"description": "Auth rate limit exceeded"},
}
ERROR_RESPONSES_AUTH_REGISTER = {
    400: {"description": "Invalid bootstrap request"},
    403: {"description": "Bootstrap unavailable or plan limit reached"},
    409: {"description": "Email already exists"},
    429: {"description": "Auth rate limit exceeded"},
}
DBA_ROLE_REQUIRED_DESCRIPTION = "DBA role required"
ERROR_RESPONSES_DBA_ONLY = {403: {"description": DBA_ROLE_REQUIRED_DESCRIPTION}}
ERROR_RESPONSES_USER_MUTATION = {
    400: {"description": "Invalid user mutation"},
    403: {"description": "DBA role required"},
    404: {"description": "User not found"},
}
ERROR_RESPONSES_INCIDENT_MUTATION = {
    403: {"description": "Insufficient role"},
    404: {"description": INCIDENT_NOT_FOUND_DETAIL},
    429: {"description": API_RATE_LIMIT_DESCRIPTION},
}
ERROR_RESPONSES_INCIDENT_READ = {
    403: {"description": "Insufficient permissions"},
    404: {"description": INCIDENT_NOT_FOUND_DETAIL},
    429: {"description": API_RATE_LIMIT_DESCRIPTION},
}
ERROR_RESPONSES_REPORT_EXECUTION = {
    400: {"description": "Invalid report request"},
    403: {"description": "Insufficient permissions for report"},
    404: {"description": "Unknown report"},
    429: {"description": API_RATE_LIMIT_DESCRIPTION},
}
ERROR_RESPONSES_SCHEDULE_MUTATION = {
    400: {"description": "Invalid schedule request"},
    403: {"description": "DBA role required or plan limit reached"},
    404: {"description": "Unknown report or schedule not found"},
}
ERROR_RESPONSES_BILLING_CHECKOUT = {
    400: {"description": "Invalid Stripe checkout request"},
    403: {"description": DBA_ROLE_REQUIRED_DESCRIPTION},
    503: {"description": "Stripe billing is not configured"},
}
ERROR_RESPONSES_BILLING_WEBHOOK = {
    400: {"description": "Invalid Stripe webhook request"},
    503: {"description": "Stripe billing is not configured"},
}

DbDep: TypeAlias = Annotated[Session, Depends(get_db)]
CurrentUserDep: TypeAlias = Annotated[User, Depends(get_current_user)]
DbaUserDep: TypeAlias = Annotated[User, Depends(require_roles("DBA"))]
RoleUserDep: TypeAlias = Callable[..., User]

ONBOARDING_STEPS: list[tuple[str, str]] = [
    ("first_user_created", "Create first team member"),
    ("first_incident_created", "Create first incident"),
    ("first_report_run", "Run first report"),
    ("first_schedule_created", "Create first schedule"),
]


def _api_rate_limit_dependency(bucket: str):
    def _check(request: Request) -> None:
        host = request.client.host if request.client else None
        if not check_api_rate_limit(host, bucket):
            raise HTTPException(status_code=429, detail=API_RATE_LIMIT_DETAIL)
    return _check


def _log_user_admin_action(
    db: Session,
    *,
    actor_user_id: int,
    target_user_id: int | None,
    target_email: str,
    action: str,
    details: dict,
) -> None:
    db.add(
        UserAdminAuditLog(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            target_email=target_email.lower(),
            action=action,
            details_json=json.dumps(details, sort_keys=True),
        )
    )


def _log_incident_history(
    db: Session,
    *,
    incident_id: int,
    actor_user_id: int | None,
    action: str,
    details: dict,
) -> None:
    db.add(
        IncidentHistory(
            incident_id=incident_id,
            actor_user_id=actor_user_id,
            action=action,
            details_json=json.dumps(details, sort_keys=True),
        )
    )


def _csv_text(columns: list[str], rows: list[dict]) -> str:
    buf = StringIO()
    writer = DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _report_schedule_read(schedule: ReportSchedule, created_by_email: str) -> ReportScheduleRead:
    try:
        params = json.loads(schedule.params_json)
    except json.JSONDecodeError:
        params = {}
    return ReportScheduleRead(
        id=schedule.id,
        report_key=schedule.report_key,
        params=params,
        cadence=schedule.cadence,
        weekday_utc=schedule.weekday_utc,
        run_hour_utc=schedule.run_hour_utc,
        run_minute_utc=schedule.run_minute_utc,
        delivery_kind=schedule.delivery_kind,
        delivery_target=schedule.delivery_target,
        notify_on_success=schedule.notify_on_success,
        notify_on_failure=schedule.notify_on_failure,
        is_enabled=schedule.is_enabled,
        next_run_at=schedule.next_run_at,
        last_run_at=schedule.last_run_at,
        last_success_at=schedule.last_success_at,
        last_error=schedule.last_error,
        created_at=schedule.created_at,
        created_by_user_id=schedule.created_by_user_id,
        created_by_email=created_by_email,
    )


def _get_or_create_billing_settings(db: Session) -> BillingSettings:
    settings = db.query(BillingSettings).filter(BillingSettings.id == 1).first()
    if settings is not None:
        return settings
    settings = BillingSettings(id=1)
    db.add(settings)
    db.flush()
    return settings


def _stripe_required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    raise RuntimeError(f"Missing required billing configuration: {name}")


def _stripe_client():
    if stripe is None:
        raise RuntimeError("Stripe SDK is not installed")
    stripe.api_key = _stripe_required_setting("STRIPE_SECRET_KEY")
    return stripe


def _stripe_get(value: Any, key: str) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _stripe_event_object(event: Any) -> Any:
    data = _stripe_get(event, "data")
    return _stripe_get(data, "object")


def _stripe_default_price_id(default_price: Any) -> str | None:
    if isinstance(default_price, str) and default_price.startswith("price_"):
        return default_price
    if isinstance(default_price, dict):
        default_price_id = _stripe_get(default_price, "id")
        if isinstance(default_price_id, str) and default_price_id.startswith("price_"):
            return default_price_id
    return None


def _stripe_first_active_price_id(stripe_client: Any, product_id: str) -> str | None:
    prices = stripe_client.Price.list(product=product_id, active=True, limit=1)
    rows = _stripe_get(prices, "data") or []
    if not rows:
        return None
    first_id = _stripe_get(rows[0], "id")
    if isinstance(first_id, str) and first_id.startswith("price_"):
        return first_id
    return None


def _resolve_stripe_checkout_price_id(stripe_client: Any, raw_id: str) -> str:
    candidate = (raw_id or "").strip()
    if not candidate:
        raise HTTPException(status_code=400, detail="Missing Stripe price identifier")
    if candidate.startswith("price_"):
        return candidate
    if candidate.startswith("prod_"):
        try:
            product = stripe_client.Product.retrieve(candidate)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Stripe product lookup failed: {str(exc)}")

        default_price = _stripe_get(product, "default_price")
        default_price_id = _stripe_default_price_id(default_price)
        if default_price_id is not None:
            return default_price_id

        try:
            active_price_id = _stripe_first_active_price_id(stripe_client, candidate)
            if active_price_id is not None:
                return active_price_id
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Stripe price lookup failed: {str(exc)}")

        raise HTTPException(
            status_code=400,
            detail="Provided Stripe product has no active/default price. Create a recurring price in Stripe first.",
        )

    raise HTTPException(
        status_code=400,
        detail="Invalid Stripe ID. Use a price_... ID (or prod_... with default/active price).",
    )


def _apply_checkout_completed_event(settings: BillingSettings, event_object: Any) -> None:
    customer_id = _stripe_get(event_object, "customer")
    subscription_id = _stripe_get(event_object, "subscription")
    if customer_id:
        settings.stripe_customer_id = str(customer_id)
    if subscription_id:
        settings.stripe_subscription_id = str(subscription_id)
    settings.billing_status = "active"


def _apply_subscription_event(settings: BillingSettings, event_object: Any) -> None:
    customer_id = _stripe_get(event_object, "customer")
    subscription_id = _stripe_get(event_object, "id")
    subscription_status = _stripe_get(event_object, "status")
    if customer_id:
        settings.stripe_customer_id = str(customer_id)
    if subscription_id:
        settings.stripe_subscription_id = str(subscription_id)
    if isinstance(subscription_status, str) and subscription_status:
        settings.billing_status = subscription_status


def _enforce_plan_limit(db: Session, *, metric: str, current_count: int) -> None:
    settings = _get_or_create_billing_settings(db)
    limit = settings.max_users if metric == "users" else settings.max_schedules
    if current_count >= limit:
        label = "users" if metric == "users" else "schedules"
        raise HTTPException(status_code=403, detail=f"Plan limit reached: max {label} is {limit} for the current plan.")


def _record_onboarding_event(db: Session, *, event_key: str, actor_user_id: int | None, details: dict | None = None) -> None:
    exists = db.query(OnboardingEvent).filter(OnboardingEvent.event_key == event_key).first()
    if exists is not None:
        return
    db.add(
        OnboardingEvent(
            event_key=event_key,
            actor_user_id=actor_user_id,
            details_json=json.dumps(details or {}, sort_keys=True),
        )
    )


def _record_string_incident_change(changes: dict[str, dict[str, Any]], incident: Incident, field_name: str, new_value: str | None) -> None:
    current_value = getattr(incident, field_name)
    if new_value is None or new_value == current_value:
        return
    changes[field_name] = {"before": current_value, "after": new_value}
    setattr(incident, field_name, new_value)


def _record_due_at_incident_change(
    changes: dict[str, dict[str, Any]],
    incident: Incident,
    new_due_at: datetime | None,
) -> None:
    before = incident.due_at.isoformat() if incident.due_at else None
    after = new_due_at.isoformat() if new_due_at else None
    if before != after:
        changes["due_at"] = {"before": before, "after": after}
    incident.due_at = new_due_at


def _bulk_acknowledge_incident(db: Session, *, incident: Incident, actor_user_id: int) -> None:
    _log_incident_history(
        db,
        incident_id=incident.id,
        actor_user_id=actor_user_id,
        action="acknowledged",
        details={"status": incident.status},
    )


def _bulk_assign_incident(db: Session, *, incident: Incident, actor_user_id: int, owner: str) -> None:
    _log_incident_history(
        db,
        incident_id=incident.id,
        actor_user_id=actor_user_id,
        action="assigned",
        details={"owner": {"before": incident.owner, "after": owner}},
    )
    incident.owner = owner


def _bulk_escalate_incident(db: Session, *, incident: Incident, actor_user_id: int) -> None:
    _log_incident_history(
        db,
        incident_id=incident.id,
        actor_user_id=actor_user_id,
        action="escalated",
        details={"severity": {"before": incident.severity, "after": "high"}},
    )
    incident.severity = "high"


def _bulk_resolve_incident(db: Session, *, incident: Incident, actor_user_id: int) -> None:
    _log_incident_history(
        db,
        incident_id=incident.id,
        actor_user_id=actor_user_id,
        action="resolved",
        details={"status": {"before": incident.status, "after": "resolved"}},
    )
    incident.status = "resolved"


def _apply_bulk_incident_action(
    db: Session,
    *,
    incident: Incident,
    action: str,
    actor_user_id: int,
    owner: str | None,
) -> None:
    if action == "acknowledge":
        _bulk_acknowledge_incident(db, incident=incident, actor_user_id=actor_user_id)
        return
    if action == "assign" and owner is not None:
        _bulk_assign_incident(db, incident=incident, actor_user_id=actor_user_id, owner=owner)
        return
    if action == "escalate":
        _bulk_escalate_incident(db, incident=incident, actor_user_id=actor_user_id)
        return
    if action == "resolve":
        _bulk_resolve_incident(db, incident=incident, actor_user_id=actor_user_id)


def _bulk_action_skip_reason(
    *,
    incident: Incident,
    action: str,
    owner: str | None,
) -> str | None:
    if incident.status != "open":
        return "incident is not open"
    if action == "assign" and owner is not None and incident.owner == owner:
        return "owner already set"
    if action == "escalate" and incident.severity == "high":
        return "incident already high severity"
    return None


def _incident_audit_snapshot(incident: Incident) -> dict[str, Any]:
    return {
        "status": incident.status,
        "severity": incident.severity,
        "owner": incident.owner,
    }


def _build_bulk_item_result(
    *,
    incident: Incident,
    outcome: str,
    reason: str | None,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> IncidentBulkActionResult.ItemResult:
    return IncidentBulkActionResult.ItemResult(
        incident_id=incident.id,
        outcome=outcome,
        reason=reason,
        before=before,
        after=after,
    )


def _build_onboarding_read(db: Session) -> list[OnboardingItemRead]:
    existing = {row.event_key: row for row in db.query(OnboardingEvent).all()}
    return [
        OnboardingItemRead(
            key=key,
            label=label,
            completed=key in existing,
            completed_at=existing[key].created_at if key in existing else None,
        )
        for key, label in ONBOARDING_STEPS
    ]


def _build_admin_metrics(db: Session) -> AdminMetricsRead:
    now = datetime.now(UTC).replace(tzinfo=None)
    window_start = now - timedelta(hours=24)
    recent_runs = db.query(ReportExecutionLog).filter(ReportExecutionLog.created_at >= window_start)
    completed_steps = db.query(OnboardingEvent).count()
    open_q = db.query(Incident).filter(Incident.status == "open")
    return AdminMetricsRead(
        total_users=db.query(User).count(),
        active_users=db.query(User).filter(User.is_active.is_(True)).count(),
        open_incidents=open_q.count(),
        resolved_incidents=db.query(Incident).filter(Incident.status == "resolved").count(),
        overdue_incidents=open_q.filter(Incident.due_at.isnot(None), Incident.due_at < now).count(),
        incidents_with_sla=open_q.filter(Incident.due_at.isnot(None)).count(),
        enabled_schedules=db.query(ReportSchedule).filter(ReportSchedule.is_enabled.is_(True)).count(),
        report_runs_last_24h=recent_runs.count(),
        successful_report_runs_last_24h=recent_runs.filter(ReportExecutionLog.success.is_(True)).count(),
        onboarding_completed_steps=min(completed_steps, len(ONBOARDING_STEPS)),
        onboarding_total_steps=len(ONBOARDING_STEPS),
    )


def _build_plan_usage(db: Session, settings: BillingSettings) -> PlanUsageRead:
    user_slots_used = db.query(User).count()
    schedule_slots_used = db.query(ReportSchedule).count()
    return PlanUsageRead(
        user_slots_used=user_slots_used,
        user_slots_remaining=max(settings.max_users - user_slots_used, 0),
        users_at_limit=user_slots_used >= settings.max_users,
        schedule_slots_used=schedule_slots_used,
        schedule_slots_remaining=max(settings.max_schedules - schedule_slots_used, 0),
        schedules_at_limit=schedule_slots_used >= settings.max_schedules,
    )


def _build_activity_trend(db: Session) -> list[ActivityTrendPointRead]:
    today = datetime.now(UTC).date()
    points: list[ActivityTrendPointRead] = []
    for days_ago in range(6, -1, -1):
        day = today - timedelta(days=days_ago)
        start = datetime.combine(day, time.min)
        end = start + timedelta(days=1)
        points.append(
            ActivityTrendPointRead(
                day=day.isoformat(),
                label=day.strftime("%a"),
                incidents_created=db.query(Incident).filter(Incident.created_at >= start, Incident.created_at < end).count(),
                report_runs=db.query(ReportExecutionLog)
                .filter(ReportExecutionLog.created_at >= start, ReportExecutionLog.created_at < end)
                .count(),
                schedules_created=db.query(ReportSchedule)
                .filter(ReportSchedule.created_at >= start, ReportSchedule.created_at < end)
                .count(),
            )
        )
    return points


def _build_admin_overview(db: Session) -> AdminOverviewRead:
    settings = _get_or_create_billing_settings(db)
    db.flush()
    return AdminOverviewRead(
        metrics=_build_admin_metrics(db),
        billing=BillingSettingsRead.model_validate(settings),
        plan_usage=_build_plan_usage(db, settings),
        onboarding=_build_onboarding_read(db),
        activity_trend=_build_activity_trend(db),
    )


def _parse_cors_origins(raw: str | None) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    for part in raw.replace("\r", "").split(","):
        o = part.strip().strip('"').strip("'").rstrip("/")
        if o:
            out.append(o)
    return out


_frontend_origins = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
).strip()
_parsed_origins = _parse_cors_origins(_frontend_origins)
allow_origins = _parsed_origins if _parsed_origins else [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

_cors_kw: dict = {
    "allow_origins": allow_origins,
    "allow_credentials": False,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
# Lets any *.onrender.com static site call this API (JWT still required for protected routes).
if os.getenv("CORS_DISABLE_RENDER_REGEX", "").lower() not in ("1", "true", "yes"):
    _cors_kw["allow_origin_regex"] = r"^https://[a-zA-Z0-9\-]+\.onrender\.com$"


@app.middleware("http")
async def request_id_access_log_middleware(request: Request, call_next):
    raw = request.headers.get("x-request-id") or request.headers.get("X-Request-ID")
    rid = (raw or "").strip() or str(uuid.uuid4())
    if len(rid) > 128:
        rid = rid[:128]
    token = set_request_id(rid)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        ACCESS_LOG.info("%s %s %s", request.method, request.url.path, response.status_code)
        return response
    finally:
        reset_request_id(token)


app.add_middleware(CORSMiddleware, **_cors_kw)


@app.get("/health")
def health(response: Response):
    """Liveness plus PostgreSQL connectivity (SELECT 1). Returns 503 if DB unreachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return {"status": "degraded", "database": "unreachable"}
    return {"status": "ok", "database": "reachable"}


@app.get("/health/scheduler")
def health_scheduler():
    disabled = os.getenv("SCHEDULED_REPORTS_DISABLE_LOOP", "").lower() in ("1", "true", "yes")
    poll_seconds = max(int(os.getenv("SCHEDULED_REPORTS_POLL_SECONDS", "60")), 5)
    return {
        "status": "ok",
        "scheduler": {
            "loop_enabled": not disabled,
            "poll_seconds": poll_seconds,
            **get_scheduler_runtime_status(),
        },
    }


STRIPE_WEBHOOK_EVENTS = (
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
)


def _stripe_env_configured(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


@app.get("/health/billing")
def health_billing(response: Response):
    """Stripe env presence only (no secret values). Use after setting Render env vars."""
    config = {
        "stripe_secret_key": _stripe_env_configured("STRIPE_SECRET_KEY"),
        "stripe_webhook_secret": _stripe_env_configured("STRIPE_WEBHOOK_SECRET"),
        "stripe_price_id_starter": _stripe_env_configured("STRIPE_PRICE_ID_STARTER"),
        "stripe_sdk_installed": stripe is not None,
    }
    ready = all(
        [
            config["stripe_secret_key"],
            config["stripe_webhook_secret"],
            config["stripe_price_id_starter"],
            config["stripe_sdk_installed"],
        ]
    )
    if not ready:
        response.status_code = 503
    return {
        "status": "ok" if ready else "degraded",
        "billing": config,
        "webhook_url_path": "/billing/webhook",
        "required_webhook_events": list(STRIPE_WEBHOOK_EVENTS),
    }


_OIDC_ENV_VARS = ("OIDC_ISSUER", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET")
_SMTP_ENV_VARS = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM")


@app.get("/health/oidc")
def health_oidc(response: Response):
    """OIDC env presence check. No secrets returned. Verify: GET /health/oidc"""
    config = {var.lower(): _stripe_env_configured(var) for var in _OIDC_ENV_VARS}
    ready = config["oidc_issuer"] and config["oidc_client_id"]
    if not ready:
        response.status_code = 503
    return {
        "status": "ok" if ready else "degraded",
        "oidc": config,
        "note": "Set OIDC_ISSUER and OIDC_CLIENT_ID to enable SSO login.",
    }


@app.get("/auth/oidc/config")
def oidc_config_endpoint():
    """Public OIDC config for the frontend SSO flow. No secrets returned."""
    if not _oidc.oidc_configured():
        raise HTTPException(status_code=404, detail="OIDC is not configured")
    try:
        auth_endpoint = _oidc.get_authorization_endpoint()
    except Exception as exc:
        logger.warning("OIDC discovery failed: %s", exc)
        raise HTTPException(status_code=503, detail="OIDC provider discovery failed")
    return {
        "authorization_endpoint": auth_endpoint,
        "client_id": _oidc.get_oidc_client_id(),
        "scope": "openid email profile",
    }


@app.post("/auth/oidc/callback", response_model=Token)
def oidc_callback(payload: OidcCallbackRequest, db: DbDep):
    """Exchange a PKCE authorization code for a DBOps access token."""
    if not _oidc.oidc_configured():
        raise HTTPException(status_code=503, detail="OIDC is not configured")
    try:
        token_response = _oidc.exchange_authorization_code(
            code=payload.code,
            redirect_uri=payload.redirect_uri,
            code_verifier=payload.code_verifier,
        )
    except Exception as exc:
        logger.warning("OIDC code exchange failed: %s", exc)
        raise HTTPException(status_code=401, detail="OIDC code exchange failed")
    id_token = token_response.get("id_token")
    if not id_token:
        raise HTTPException(status_code=401, detail="Provider did not return an ID token")
    try:
        claims = _oidc.verify_oidc_id_token(id_token)
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=401, detail=f"Invalid ID token: {exc}")
    except Exception as exc:
        logger.warning("OIDC token verification error: %s", exc)
        raise HTTPException(status_code=503, detail="OIDC token verification failed")
    email = claims["email"].lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        default_role = _oidc.get_oidc_default_role()
        user = User(email=email, hashed_password="", role=default_role, is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        _log_user_admin_action(
            db,
            actor_user_id=user.id,
            target_user_id=user.id,
            target_email=email,
            action="oidc_auto_provision",
            details={"role": default_role},
        )
        db.commit()
    elif not user.is_active:
        raise HTTPException(status_code=403, detail=ACCOUNT_DISABLED_DETAIL)
    return Token(access_token=create_access_token(str(user.id), user.role))


@app.get("/health/smtp")
def health_smtp(response: Response):
    """SMTP env presence check (no secret values). Shows whether email delivery is configured."""
    config = {var.lower(): _stripe_env_configured(var) for var in _SMTP_ENV_VARS}
    host_set = config["smtp_host"]
    if not host_set:
        response.status_code = 503
    return {
        "status": "ok" if host_set else "degraded",
        "smtp": config,
        "note": "Only SMTP_HOST is required; SMTP_USER/SMTP_PASSWORD needed for auth; SMTP_FROM defaults to SMTP_USER.",
    }


@app.get("/admin/overview", response_model=AdminOverviewRead)
def admin_overview(
    db: DbDep,
    _: DbaUserDep,
):
    overview = _build_admin_overview(db)
    db.commit()
    return overview


@app.put("/admin/billing", response_model=BillingSettingsRead, responses=ERROR_RESPONSES_DBA_ONLY)
def update_billing_settings(
    payload: BillingSettingsUpdate,
    db: DbDep,
    _: DbaUserDep,
):
    settings = _get_or_create_billing_settings(db)
    settings.plan_key = payload.plan_key
    settings.billing_status = payload.billing_status
    settings.monthly_price_cents = payload.monthly_price_cents
    settings.max_users = payload.max_users
    settings.max_schedules = payload.max_schedules
    settings.stripe_customer_id = payload.stripe_customer_id
    settings.stripe_subscription_id = payload.stripe_subscription_id
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


@app.post(
    "/billing/checkout/session",
    response_model=BillingCheckoutSessionRead,
    responses=ERROR_RESPONSES_BILLING_CHECKOUT,
)
def create_billing_checkout_session(
    payload: BillingCheckoutSessionCreate,
    db: DbDep,
    current: DbaUserDep,
):
    try:
        stripe_client = _stripe_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    settings = _get_or_create_billing_settings(db)
    try:
        configured_price_or_product = payload.price_id or _stripe_required_setting("STRIPE_PRICE_ID_STARTER")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    price_id = _resolve_stripe_checkout_price_id(stripe_client, configured_price_or_product)

    try:
        session = stripe_client.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
            customer=settings.stripe_customer_id or None,
            customer_email=current.email if not settings.stripe_customer_id else None,
            metadata={"plan_key": payload.plan_key or settings.plan_key},
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Stripe checkout failed: {str(exc)}")

    session_id = _stripe_get(session, "id")
    checkout_url = _stripe_get(session, "url")
    if not session_id or not checkout_url:
        raise HTTPException(status_code=400, detail="Stripe checkout did not return a valid session")

    return BillingCheckoutSessionRead(session_id=str(session_id), url=str(checkout_url))


@app.post("/billing/webhook", response_model=StripeWebhookEventRead, responses=ERROR_RESPONSES_BILLING_WEBHOOK)
async def handle_billing_webhook(
    request: Request,
    db: DbDep,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
):
    try:
        stripe_client = _stripe_client()
        webhook_secret = _stripe_required_setting("STRIPE_WEBHOOK_SECRET")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    payload_bytes = await request.body()
    payload_text = payload_bytes.decode("utf-8")
    try:
        event = stripe_client.Webhook.construct_event(
            payload=payload_text,
            sig_header=stripe_signature,
            secret=webhook_secret,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature")

    event_type = str(_stripe_get(event, "type") or "unknown")
    settings = _get_or_create_billing_settings(db)
    event_object = _stripe_event_object(event)

    if event_type == "checkout.session.completed":
        _apply_checkout_completed_event(settings, event_object)
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        _apply_subscription_event(settings, event_object)

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return StripeWebhookEventRead(
        received=True,
        event_type=event_type,
        billing_status=settings.billing_status,
    )


@app.post("/auth/login", response_model=Token, responses=ERROR_RESPONSES_AUTH_LOGIN)
def login_json(payload: LoginRequest, request: Request, db: DbDep):
    if not check_auth_rate_limit(request.client.host if request.client else None, "auth-login"):
        raise HTTPException(status_code=429, detail=AUTH_RATE_LIMIT_DETAIL)
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail=ACCOUNT_DISABLED_DETAIL)
    token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=token)


@app.post("/auth/token", response_model=Token, responses=ERROR_RESPONSES_AUTH_LOGIN)
def login_form(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDep,
):
    if not check_auth_rate_limit(request.client.host if request.client else None, "auth-token"):
        raise HTTPException(status_code=429, detail=AUTH_RATE_LIMIT_DETAIL)
    user = db.query(User).filter(User.email == form_data.username.lower()).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail=ACCOUNT_DISABLED_DETAIL)
    token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=token)


@app.get("/auth/me", response_model=UserRead)
def me(current: CurrentUserDep):
    return current


@app.post("/auth/register", response_model=UserRead, status_code=201, responses=ERROR_RESPONSES_AUTH_REGISTER)
def register_bootstrap(payload: UserCreate, request: Request, db: DbDep):
    """First user only (role must be DBA). Further accounts use POST /auth/users as DBA."""
    if not check_auth_rate_limit(request.client.host if request.client else None, "auth-register"):
        raise HTTPException(status_code=429, detail=AUTH_RATE_LIMIT_DETAIL)
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=403,
            detail="Bootstrap complete. Use POST /auth/users with a DBA token.",
        )
    if payload.role != "DBA":
        raise HTTPException(
            status_code=400,
            detail="First registered user must have role DBA",
        )

    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/users", response_model=UserRead, status_code=201, responses=ERROR_RESPONSES_AUTH_REGISTER)
def register_as_dba(
    payload: UserCreate,
    db: DbDep,
    current: DbaUserDep,
):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    _enforce_plan_limit(db, metric="users", current_count=db.query(User).count())
    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.flush()
    _log_user_admin_action(
        db,
        actor_user_id=current.id,
        target_user_id=user.id,
        target_email=user.email,
        action="create_user",
        details={"role": user.role},
    )
    _record_onboarding_event(
        db,
        event_key="first_user_created",
        actor_user_id=current.id,
        details={"created_email": user.email},
    )
    db.commit()
    db.refresh(user)
    return user


@app.get("/auth/users", response_model=list[UserRead])
def list_users(
    db: DbDep,
    _: DbaUserDep,
):
    """So DBAs can confirm accounts and avoid duplicate-email surprises."""
    return db.query(User).order_by(User.id.asc()).all()


@app.get("/auth/users/audit", response_model=list[UserAdminAuditRead])
def list_user_admin_audit(
    db: DbDep,
    _: DbaUserDep,
    limit: int = 100,
):
    limit = min(max(limit, 1), 500)
    actor_user = User.__table__.alias("actor_user")
    rows = (
        db.query(
            UserAdminAuditLog,
            actor_user.c.email,
        )
        .outerjoin(actor_user, UserAdminAuditLog.actor_user_id == actor_user.c.id)
        .order_by(UserAdminAuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    out: list[UserAdminAuditRead] = []
    for audit, actor_email in rows:
        try:
            details = json.loads(audit.details_json)
        except json.JSONDecodeError:
            details = {}
        out.append(
            UserAdminAuditRead(
                id=audit.id,
                actor_user_id=audit.actor_user_id,
                actor_email=actor_email,
                target_user_id=audit.target_user_id,
                target_email=audit.target_email,
                action=audit.action,
                details=details,
                created_at=audit.created_at,
            )
        )
    return out


@app.patch("/auth/users/{user_id}/password", response_model=UserRead, responses=ERROR_RESPONSES_USER_MUTATION)
def reset_user_password(
    user_id: int,
    payload: UserPasswordReset,
    db: DbDep,
    current: DbaUserDep,
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND_DETAIL)
    user.hashed_password = hash_password(payload.password)
    _log_user_admin_action(
        db,
        actor_user_id=current.id,
        target_user_id=user.id,
        target_email=user.email,
        action="reset_password",
        details={"password_reset": True},
    )
    db.commit()
    db.refresh(user)
    return user


@app.patch("/auth/users/{user_id}/status", response_model=UserRead, responses=ERROR_RESPONSES_USER_MUTATION)
def set_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: DbDep,
    current: DbaUserDep,
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND_DETAIL)
    if current.id == user.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    user.is_active = payload.is_active
    _log_user_admin_action(
        db,
        actor_user_id=current.id,
        target_user_id=user.id,
        target_email=user.email,
        action="set_status",
        details={"is_active": payload.is_active},
    )
    db.commit()
    db.refresh(user)
    return user


@app.delete("/auth/users/{user_id}", status_code=204, responses=ERROR_RESPONSES_USER_MUTATION)
def delete_user(
    user_id: int,
    db: DbDep,
    current: DbaUserDep,
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND_DETAIL)
    if current.id == user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    target_id = user.id
    target_email = user.email
    _log_user_admin_action(
        db,
        actor_user_id=current.id,
        target_user_id=target_id,
        target_email=target_email,
        action="delete_user",
        details={"deleted": True},
    )
    db.delete(user)
    db.commit()


IncidentStatusQuery = Annotated[str | None, Query()]
IncidentSeverityQuery = Annotated[str | None, Query()]
IncidentOwnerQuery = Annotated[str | None, Query()]
IncidentSearchQuery = Annotated[str | None, Query(min_length=1, max_length=120)]
IncidentStartDateQuery = Annotated[date | None, Query()]
IncidentEndDateQuery = Annotated[date | None, Query()]
IncidentSortQuery = Annotated[str, Query(pattern="^(newest|oldest|severity)$")]
IncidentOverdueQuery = Annotated[bool | None, Query(description="If true, only open incidents with due_at in the past")]


@app.get("/incidents", response_model=list[IncidentRead])
def list_incidents(
    db: DbDep,
    _: Annotated[User, Depends(require_roles("DBA", "Analyst", "Viewer"))],
    status: IncidentStatusQuery = None,
    severity: IncidentSeverityQuery = None,
    owner: IncidentOwnerQuery = None,
    search: IncidentSearchQuery = None,
    start_date: IncidentStartDateQuery = None,
    end_date: IncidentEndDateQuery = None,
    overdue: IncidentOverdueQuery = None,
    sort: IncidentSortQuery = "newest",
):
    query = db.query(Incident)

    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)
    if owner:
        query = query.filter(Incident.owner.ilike(f"%{owner}%"))
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                Incident.title.ilike(like_term),
                Incident.description.ilike(like_term),
                Incident.owner.ilike(like_term),
            )
        )
    if start_date:
        query = query.filter(Incident.created_at >= datetime.combine(start_date, time.min))
    if end_date:
        query = query.filter(Incident.created_at < datetime.combine(end_date + timedelta(days=1), time.min))
    if overdue is True:
        now = datetime.now(UTC).replace(tzinfo=None)
        query = query.filter(
            Incident.status == "open",
            Incident.due_at.isnot(None),
            Incident.due_at < now,
        )

    if sort == "oldest":
        query = query.order_by(Incident.created_at.asc())
    elif sort == "severity":
        severity_rank = case(
            (Incident.severity == "high", 1),
            (Incident.severity == "medium", 2),
            (Incident.severity == "low", 3),
            else_=4,
        )
        query = query.order_by(severity_rank.asc(), Incident.created_at.desc())
    else:
        query = query.order_by(Incident.created_at.desc())

    return query.all()


@app.post(
    "/incidents",
    response_model=IncidentRead,
    status_code=201,
    responses={403: {"description": "Insufficient role"}, 429: {"description": API_RATE_LIMIT_DESCRIPTION}},
    dependencies=[Depends(_api_rate_limit_dependency("incidents_create"))],
)
def create_incident(
    payload: IncidentCreate,
    db: DbDep,
    current: Annotated[User, Depends(require_roles("DBA", "Analyst"))],
):
    incident = Incident(
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        owner=payload.owner,
        status="open",
        due_at=payload.due_at,
    )
    db.add(incident)
    db.flush()
    _record_onboarding_event(
        db,
        event_key="first_incident_created",
        actor_user_id=current.id,
        details={"incident_id": incident.id},
    )
    _log_incident_history(
        db,
        incident_id=incident.id,
        actor_user_id=current.id,
        action="created",
        details={
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity,
            "owner": incident.owner,
            "status": incident.status,
            "due_at": incident.due_at.isoformat() if incident.due_at else None,
        },
    )
    db.commit()
    db.refresh(incident)
    return incident


@app.patch("/incidents/{incident_id}", response_model=IncidentRead, responses=ERROR_RESPONSES_INCIDENT_MUTATION)
def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: DbDep,
    current: Annotated[User, Depends(require_roles("DBA", "Analyst"))],
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=INCIDENT_NOT_FOUND_DETAIL)

    changes: dict[str, dict[str, Any]] = {}
    _record_string_incident_change(changes, incident, "title", payload.title)
    _record_string_incident_change(changes, incident, "description", payload.description)
    _record_string_incident_change(changes, incident, "severity", payload.severity)
    _record_string_incident_change(changes, incident, "owner", payload.owner)

    payload_updates = payload.model_dump(exclude_unset=True)
    if "due_at" in payload_updates:
        _record_due_at_incident_change(changes, incident, payload_updates["due_at"])

    if changes:
        _log_incident_history(
            db,
            incident_id=incident.id,
            actor_user_id=current.id,
            action="updated",
            details={"changes": changes},
        )

    db.commit()
    db.refresh(incident)
    return incident


@app.patch("/incidents/{incident_id}/resolve", response_model=IncidentRead, responses=ERROR_RESPONSES_INCIDENT_MUTATION)
def resolve_incident(
    incident_id: int,
    db: DbDep,
    current: DbaUserDep,
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=INCIDENT_NOT_FOUND_DETAIL)
    if incident.status != "resolved":
        _log_incident_history(
            db,
            incident_id=incident.id,
            actor_user_id=current.id,
            action="resolved",
            details={"status": {"before": incident.status, "after": "resolved"}},
        )
    incident.status = "resolved"
    db.commit()
    db.refresh(incident)
    return incident


@app.patch(
    "/incidents/actions/bulk",
    response_model=IncidentBulkActionResult,
    responses=ERROR_RESPONSES_INCIDENT_MUTATION,
    dependencies=[Depends(_api_rate_limit_dependency("incidents_mutation"))],
)
def bulk_incident_action(
    payload: IncidentBulkActionRequest,
    db: DbDep,
    current: Annotated[User, Depends(require_roles("DBA", "Analyst"))],
):
    requested_count = len(payload.incident_ids)
    unique_ids = list(dict.fromkeys(payload.incident_ids))
    duplicate_count = requested_count - len(unique_ids)
    incidents = db.query(Incident).filter(Incident.id.in_(unique_ids)).all()
    if len(incidents) != len(unique_ids):
        found_ids = {incident.id for incident in incidents}
        missing = sorted([incident_id for incident_id in unique_ids if incident_id not in found_ids])
        raise HTTPException(status_code=404, detail=f"Incidents not found: {', '.join(str(v) for v in missing)}")

    if payload.action == "resolve" and current.role != "DBA":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    incidents_by_id = {incident.id: incident for incident in incidents}
    ordered_incidents = [incidents_by_id[incident_id] for incident_id in unique_ids]
    item_results: list[IncidentBulkActionResult.ItemResult] = []
    updated_incidents: list[Incident] = []

    for incident in ordered_incidents:
        skip_reason = _bulk_action_skip_reason(incident=incident, action=payload.action, owner=payload.owner)
        if skip_reason is not None:
            item_results.append(
                _build_bulk_item_result(
                    incident=incident,
                    outcome="skipped",
                    reason=skip_reason,
                    before=_incident_audit_snapshot(incident),
                    after=_incident_audit_snapshot(incident),
                )
            )
            continue

        before = _incident_audit_snapshot(incident)
        _apply_bulk_incident_action(
            db,
            incident=incident,
            action=payload.action,
            actor_user_id=current.id,
            owner=payload.owner,
        )
        after = _incident_audit_snapshot(incident)
        item_results.append(
            _build_bulk_item_result(
                incident=incident,
                outcome="updated",
                reason=None,
                before=before,
                after=after,
            )
        )
        updated_incidents.append(incident)

    db.commit()
    for incident in ordered_incidents:
        db.refresh(incident)

    updated_count = len(updated_incidents)
    skipped_count = len(item_results) - updated_count

    return IncidentBulkActionResult(
        action=payload.action,
        affected_count=updated_count,
        incidents=ordered_incidents,
        summary=IncidentBulkActionResult.Summary(
            requested_count=requested_count,
            unique_count=len(unique_ids),
            duplicate_count=duplicate_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
        ),
        items=item_results,
    )


@app.get(
    "/incidents/{incident_id}/history",
    response_model=list[IncidentHistoryRead],
    responses=ERROR_RESPONSES_INCIDENT_READ,
)
def get_incident_history(
    incident_id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_roles("DBA", "Analyst", "Viewer"))],
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=INCIDENT_NOT_FOUND_DETAIL)
    rows = (
        db.query(IncidentHistory, User.email)
        .outerjoin(User, IncidentHistory.actor_user_id == User.id)
        .filter(IncidentHistory.incident_id == incident_id)
        .order_by(IncidentHistory.created_at.asc(), IncidentHistory.id.asc())
        .all()
    )
    out: list[IncidentHistoryRead] = []
    for hist, actor_email in rows:
        try:
            details = json.loads(hist.details_json or "{}")
        except json.JSONDecodeError:
            details = {}
        out.append(
            IncidentHistoryRead(
                id=hist.id,
                incident_id=hist.incident_id,
                actor_email=actor_email,
                action=hist.action,
                details=details,
                created_at=hist.created_at,
            )
        )
    return out


@app.get(
    "/incidents/{incident_id}/history/export",
    response_class=PlainTextResponse,
    responses=ERROR_RESPONSES_INCIDENT_READ,
)
def export_incident_history_csv(
    incident_id: int,
    db: DbDep,
    _: Annotated[User, Depends(require_roles("DBA", "Analyst", "Viewer"))],
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=INCIDENT_NOT_FOUND_DETAIL)
    rows = (
        db.query(IncidentHistory, User.email)
        .outerjoin(User, IncidentHistory.actor_user_id == User.id)
        .filter(IncidentHistory.incident_id == incident_id)
        .order_by(IncidentHistory.created_at.asc(), IncidentHistory.id.asc())
        .all()
    )
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "incident_id", "created_at", "actor_email", "action", "details_json"])
    for hist, actor_email in rows:
        writer.writerow(
            [
                hist.id,
                hist.incident_id,
                hist.created_at.isoformat() if hist.created_at else "",
                actor_email or "",
                hist.action,
                hist.details_json or "{}",
            ]
        )
    response = PlainTextResponse(buf.getvalue(), media_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="incident-{incident_id}-history.csv"'
    return response


@app.get("/reports/catalog", response_model=list[ReportCatalogEntry])
def report_catalog(current: CurrentUserDep):
    entries: list[ReportCatalogEntry] = []
    for key, spec in REPORTS.items():
        if current.role not in spec["roles"]:
            continue
        entries.append(
            ReportCatalogEntry(
                key=key,
                title=spec["title"],
                description=spec["description"],
                params=[ReportParamSpec.model_validate(p) for p in spec["params"]],
            )
        )
    return entries


@app.post(
    "/reports/run",
    response_model=ReportExecuteResponse,
    responses=ERROR_RESPONSES_REPORT_EXECUTION,
    dependencies=[Depends(_api_rate_limit_dependency("reports_run"))],
)
def run_report(
    body: ReportExecuteRequest,
    db: DbDep,
    current: CurrentUserDep,
):
    try:
        data = execute_whitelisted_report(db, current, body.report_key, body.params)
        _record_onboarding_event(
            db,
            event_key="first_report_run",
            actor_user_id=current.id,
            details={"report_key": body.report_key},
        )
        db.commit()
        return ReportExecuteResponse.model_validate(data)
    except PermissionError:
        raise HTTPException(status_code=403, detail=REPORT_PERMISSION_DETAIL)
    except ValueError as exc:
        msg = str(exc)
        code = 404 if msg.startswith(UNKNOWN_REPORT_PREFIX) else 400
        raise HTTPException(status_code=code, detail=msg)


@app.post(
    "/reports/export/csv",
    response_class=PlainTextResponse,
    responses=ERROR_RESPONSES_REPORT_EXECUTION,
    dependencies=[Depends(_api_rate_limit_dependency("reports_export_csv"))],
)
def export_report_csv(
    body: ReportExecuteRequest,
    db: DbDep,
    current: CurrentUserDep,
):
    try:
        data = execute_whitelisted_report(db, current, body.report_key, body.params)
        csv_text = _csv_text(data["columns"], data["rows"])
        response = PlainTextResponse(csv_text, media_type="text/csv")
        response.headers["Content-Disposition"] = f'attachment; filename="{body.report_key}.csv"'
        return response
    except PermissionError:
        raise HTTPException(status_code=403, detail=REPORT_PERMISSION_DETAIL)
    except ValueError as exc:
        msg = str(exc)
        code = 404 if msg.startswith(UNKNOWN_REPORT_PREFIX) else 400
        raise HTTPException(status_code=code, detail=msg)


@app.get("/reports/runs", response_model=list[ReportRunRead])
def list_report_runs(
    db: DbDep,
    _: DbaUserDep,
    limit: int = 100,
):
    limit = min(max(limit, 1), 500)
    rows = (
        db.query(ReportExecutionLog, User.email)
        .join(User, ReportExecutionLog.user_id == User.id)
        .order_by(ReportExecutionLog.created_at.desc())
        .limit(limit)
        .all()
    )
    out: list[ReportRunRead] = []
    for log, email in rows:
        try:
            params = json.loads(log.params_json)
        except json.JSONDecodeError:
            params = {}
        out.append(
            ReportRunRead(
                id=log.id,
                scheduled_report_id=log.scheduled_report_id,
                report_key=log.report_key,
                params=params,
                row_count=log.row_count,
                duration_ms=log.duration_ms,
                success=log.success,
                error_message=log.error_message,
                created_at=log.created_at,
                user_email=email,
            )
        )
    return out


@app.post("/reports/schedules", response_model=ReportScheduleRead, status_code=201, responses=ERROR_RESPONSES_SCHEDULE_MUTATION)
def create_report_schedule(
    body: ReportScheduleCreate,
    db: DbDep,
    current: DbaUserDep,
):
    try:
        _, bind_params = prepare_report_request(current, body.report_key, body.params)
    except PermissionError:
        raise HTTPException(status_code=403, detail=REPORT_PERMISSION_DETAIL)
    except ValueError as exc:
        msg = str(exc)
        code = 404 if msg.startswith(UNKNOWN_REPORT_PREFIX) else 400
        raise HTTPException(status_code=code, detail=msg)

    _enforce_plan_limit(db, metric="schedules", current_count=db.query(ReportSchedule).count())

    schedule = ReportSchedule(
        created_by_user_id=current.id,
        report_key=body.report_key,
        params_json=json.dumps(bind_params, sort_keys=True),
        cadence=body.cadence,
        weekday_utc=body.weekday_utc,
        run_hour_utc=body.run_hour_utc,
        run_minute_utc=body.run_minute_utc,
        delivery_kind=body.delivery_kind,
        delivery_target=body.delivery_target,
        notify_on_success=body.notify_on_success,
        notify_on_failure=body.notify_on_failure,
        is_enabled=True,
        next_run_at=compute_next_run_at(
            body.cadence,
            body.weekday_utc,
            body.run_hour_utc,
            body.run_minute_utc,
            datetime.now(UTC).replace(tzinfo=None),
        ),
    )
    db.add(schedule)
    db.flush()
    _record_onboarding_event(
        db,
        event_key="first_schedule_created",
        actor_user_id=current.id,
        details={"schedule_id": schedule.id, "report_key": schedule.report_key},
    )
    db.commit()
    db.refresh(schedule)
    return _report_schedule_read(schedule, current.email)


@app.get("/reports/schedules", response_model=list[ReportScheduleRead])
def list_report_schedules(
    db: DbDep,
    _: DbaUserDep,
):
    rows = (
        db.query(ReportSchedule, User.email)
        .join(User, ReportSchedule.created_by_user_id == User.id)
        .order_by(ReportSchedule.created_at.desc(), ReportSchedule.id.desc())
        .all()
    )
    return [_report_schedule_read(schedule, email) for schedule, email in rows]


@app.patch("/reports/schedules/{schedule_id}/status", response_model=ReportScheduleRead, responses=ERROR_RESPONSES_SCHEDULE_MUTATION)
def update_report_schedule_status(
    schedule_id: int,
    body: ReportScheduleStatusUpdate,
    db: DbDep,
    _: DbaUserDep,
):
    row = (
        db.query(ReportSchedule, User.email)
        .join(User, ReportSchedule.created_by_user_id == User.id)
        .filter(ReportSchedule.id == schedule_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Report schedule not found")
    schedule, email = row
    schedule.is_enabled = body.is_enabled
    if body.is_enabled:
        schedule.next_run_at = compute_next_run_at(
            schedule.cadence,
            schedule.weekday_utc,
            schedule.run_hour_utc,
            schedule.run_minute_utc,
            datetime.now(UTC).replace(tzinfo=None),
        )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return _report_schedule_read(schedule, email)


@app.get("/reports/summary")
def report_summary(
    db: DbDep,
    _: Annotated[User, Depends(require_roles("DBA", "Analyst", "Viewer"))],
):
    incidents = db.query(Incident).all()
    total = len(incidents)
    open_count = len([i for i in incidents if i.status == "open"])
    resolved_count = len([i for i in incidents if i.status == "resolved"])
    high_severity = len([i for i in incidents if i.severity == "high"])

    return {
        "total_incidents": total,
        "open_incidents": open_count,
        "resolved_incidents": resolved_count,
        "high_severity_incidents": high_severity,
    }
