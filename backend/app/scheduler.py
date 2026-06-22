import asyncio
import json
import logging
import os
import time
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from urllib import error as urlerror
from urllib import request as urlrequest

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from .db import SessionLocal
from .models import ReportExecutionLog, ReportSchedule, User
from .report_runner import execute_whitelisted_report, prepare_report_request
from .smtp_notify import send_smtp_text_email, smtp_configured

logger = logging.getLogger(__name__)

_runtime_status = {
    "last_iteration_started_at": None,
    "last_iteration_completed_at": None,
    "last_iteration_processed": 0,
    "last_iteration_error": None,
    "consecutive_failures": 0,
    "last_hosting_monitor_at": None,
    "last_hosting_monitor_should_upgrade": None,
}
_last_hosting_monitor_check_at: datetime | None = None


def get_scheduler_runtime_status() -> dict:
    return dict(_runtime_status)


def _hosting_monitor_interval_hours() -> int:
    raw = os.getenv("RAILWAY_MONITOR_INTERVAL_HOURS", "").strip() or os.getenv(
        "RENDER_MONITOR_INTERVAL_HOURS", "24"
    )
    try:
        return max(int(raw), 1)
    except ValueError:
        return 24


def maybe_run_hosting_monitor_check() -> None:
    global _last_hosting_monitor_check_at

    disable = os.getenv("RAILWAY_MONITOR_DISABLE", "").strip() or os.getenv("RENDER_MONITOR_DISABLE", "").strip()
    if disable.lower() in {"1", "true", "yes"}:
        return

    now = datetime.now(UTC).replace(tzinfo=None)
    if _last_hosting_monitor_check_at is not None:
        elapsed = now - _last_hosting_monitor_check_at
        if elapsed < timedelta(hours=_hosting_monitor_interval_hours()):
            return

    db = SessionLocal()
    try:
        from .hosting_monitor import scheduled_hosting_monitor_check

        status = scheduled_hosting_monitor_check(db)
        _last_hosting_monitor_check_at = now
        _runtime_status["last_hosting_monitor_at"] = now.isoformat()
        if status is not None:
            _runtime_status["last_hosting_monitor_should_upgrade"] = status.get("should_upgrade")
    except Exception:
        logger.exception("Railway hosting monitor scheduled check failed")
    finally:
        db.close()


def _retry_env_int(name: str, default: int, minimum: int = 0) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(value, minimum)


def compute_next_run_at(
    cadence: str,
    weekday_utc: int | None,
    run_hour_utc: int,
    run_minute_utc: int,
    now: datetime,
) -> datetime:
    candidate = now.replace(hour=run_hour_utc, minute=run_minute_utc, second=0, microsecond=0)
    if cadence == "daily":
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
    if cadence == "weekly":
        if weekday_utc is None:
            raise ValueError("weekday_utc is required for weekly schedules")
        candidate += timedelta(days=(weekday_utc - candidate.weekday()) % 7)
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate
    raise ValueError("Unsupported cadence")


def _log_schedule_failure(
    db,
    schedule: ReportSchedule,
    user_id: int,
    error_message: str,
    executed_at: datetime,
) -> None:
    db.add(
        ReportExecutionLog(
            user_id=user_id,
            scheduled_report_id=schedule.id,
            report_key=schedule.report_key,
            params_json=schedule.params_json,
            row_count=None,
            duration_ms=0,
            success=False,
            error_message=error_message[:4000],
            created_at=executed_at,
        )
    )


def _notification_payload(schedule: ReportSchedule, ok: bool, run_at: datetime, detail: str | None) -> dict:
    return {
        "schedule_id": schedule.id,
        "report_key": schedule.report_key,
        "status": "success" if ok else "failure",
        "run_at": run_at.isoformat(),
        "next_run_at": schedule.next_run_at.isoformat(),
        "delivery_kind": schedule.delivery_kind,
        "delivery_target": schedule.delivery_target,
        "detail": detail,
    }


def _send_webhook_notification(target_url: str, payload: dict) -> None:
    req = urlrequest.Request(
        target_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=3) as res:
        if res.status >= 400:
            raise RuntimeError(f"Webhook returned HTTP {res.status}")


def _send_webhook_notification_with_retry(target_url: str, payload: dict) -> None:
    attempts = _retry_env_int("SCHEDULED_REPORTS_WEBHOOK_ATTEMPTS", 2, minimum=1)
    backoff_ms = _retry_env_int("SCHEDULED_REPORTS_WEBHOOK_BACKOFF_MS", 250, minimum=0)
    for attempt in range(1, attempts + 1):
        try:
            _send_webhook_notification(target_url, payload)
            return
        except (urlerror.URLError, RuntimeError, ValueError) as exc:
            if attempt >= attempts:
                raise
            logger.warning(
                "Webhook delivery attempt %s/%s failed for %s: %s",
                attempt,
                attempts,
                target_url,
                str(exc),
            )
            if backoff_ms:
                time.sleep((backoff_ms * attempt) / 1000)


def _run_schedule_report_with_retry(db, owner: User, schedule: ReportSchedule) -> str | None:
    attempts = _retry_env_int("SCHEDULED_REPORTS_EXECUTION_ATTEMPTS", 2, minimum=1)
    backoff_ms = _retry_env_int("SCHEDULED_REPORTS_EXECUTION_BACKOFF_MS", 300, minimum=0)

    try:
        params = json.loads(schedule.params_json)
    except json.JSONDecodeError:
        return "Schedule parameters are invalid JSON"

    for attempt in range(1, attempts + 1):
        try:
            prepare_report_request(owner, schedule.report_key, params)
            execute_whitelisted_report(
                db,
                owner,
                schedule.report_key,
                params,
                scheduled_report_id=schedule.id,
            )
            return None
        except (PermissionError, ValueError) as exc:
            return str(exc)
        except Exception as exc:
            if attempt >= attempts:
                return f"{exc.__class__.__name__}: {str(exc)}"
            logger.warning(
                "Schedule %s run attempt %s/%s failed: %s",
                schedule.id,
                attempt,
                attempts,
                str(exc),
            )
            if backoff_ms:
                time.sleep((backoff_ms * attempt) / 1000)
    return "Unknown schedule execution failure"


def _dispatch_notification_hook(
    schedule: ReportSchedule,
    *,
    ok: bool,
    run_at: datetime,
    detail: str | None,
) -> None:
    if ok and not schedule.notify_on_success:
        return
    if not ok and not schedule.notify_on_failure:
        return
    if schedule.delivery_kind == "none":
        return
    payload = _notification_payload(schedule, ok, run_at, detail)
    if schedule.delivery_kind == "email":
        if not schedule.delivery_target:
            logger.warning("Schedule %s configured for email with empty target", schedule.id)
            return
        subject = f"DBOps schedule {schedule.id}: {schedule.report_key} ({payload['status']})"
        body = json.dumps(payload, indent=2, sort_keys=True)
        if smtp_configured():
            try:
                send_smtp_text_email(to_addr=schedule.delivery_target.strip(), subject=subject, body=body)
            except Exception as exc:
                logger.warning("SMTP delivery failed for schedule %s: %s", schedule.id, str(exc))
        else:
            logger.info("Scheduled report email hook (set SMTP_HOST to send): %s", payload)
        return
    if schedule.delivery_kind == "webhook":
        if not schedule.delivery_target:
            logger.warning("Schedule %s configured for webhook with empty target", schedule.id)
            return
        try:
            _send_webhook_notification_with_retry(schedule.delivery_target, payload)
        except (urlerror.URLError, RuntimeError, ValueError) as exc:
            logger.warning("Webhook delivery failed for schedule %s: %s", schedule.id, str(exc))
        return
    logger.warning("Schedule %s has unsupported delivery_kind=%s", schedule.id, schedule.delivery_kind)


_SCHEDULER_LOCK_KEY1 = 948_221
_SCHEDULER_LOCK_KEY2 = 1_129_033


def _scheduler_try_advisory_lock(db) -> bool:
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return True
    row = db.execute(
        text("SELECT pg_try_advisory_lock(:k1, :k2)"),
        {"k1": _SCHEDULER_LOCK_KEY1, "k2": _SCHEDULER_LOCK_KEY2},
    ).scalar()
    return bool(row)


def _scheduler_release_advisory_lock(db) -> None:
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    db.execute(
        text("SELECT pg_advisory_unlock(:k1, :k2)"),
        {"k1": _SCHEDULER_LOCK_KEY1, "k2": _SCHEDULER_LOCK_KEY2},
    )


def _purge_old_report_execution_logs(db, *, run_at: datetime) -> None:
    raw = os.getenv("REPORT_EXECUTION_LOG_RETENTION_DAYS", "0").strip()
    try:
        days = int(raw)
    except ValueError:
        days = 0
    if days <= 0:
        return
    cutoff = run_at - timedelta(days=days)
    deleted = db.query(ReportExecutionLog).filter(ReportExecutionLog.created_at < cutoff).delete(synchronize_session=False)
    if deleted:
        db.commit()


def process_due_report_schedules(session_factory: sessionmaker = SessionLocal, now: datetime | None = None) -> int:
    processed = 0
    run_at = now or datetime.now(UTC).replace(tzinfo=None)
    db = session_factory()
    locked = False
    try:
        if not _scheduler_try_advisory_lock(db):
            return 0
        locked = True
        _purge_old_report_execution_logs(db, run_at=run_at)

        due_schedules = (
            db.query(ReportSchedule)
            .filter(ReportSchedule.is_enabled.is_(True), ReportSchedule.next_run_at <= run_at)
            .order_by(ReportSchedule.next_run_at.asc(), ReportSchedule.id.asc())
            .all()
        )
        for schedule in due_schedules:
            next_run_at = compute_next_run_at(
                schedule.cadence,
                schedule.weekday_utc,
                schedule.run_hour_utc,
                schedule.run_minute_utc,
                run_at,
            )
            owner = db.query(User).filter(User.id == schedule.created_by_user_id).first()
            error_message = None

            if owner is None:
                schedule.is_enabled = False
                error_message = "Schedule owner no longer exists"
            elif not owner.is_active:
                error_message = "Schedule owner is disabled"
            else:
                error_message = _run_schedule_report_with_retry(db, owner, schedule)

            schedule.last_run_at = run_at
            schedule.next_run_at = next_run_at
            if error_message is None:
                schedule.last_success_at = run_at
                schedule.last_error = None
                _dispatch_notification_hook(schedule, ok=True, run_at=run_at, detail=None)
            else:
                schedule.last_error = error_message[:4000]
                _log_schedule_failure(db, schedule, schedule.created_by_user_id, error_message, run_at)
                _dispatch_notification_hook(schedule, ok=False, run_at=run_at, detail=error_message)
            db.add(schedule)
            db.commit()
            processed += 1
        return processed
    finally:
        if locked:
            try:
                _scheduler_release_advisory_lock(db)
                db.commit()
            except Exception:
                logger.exception("Failed to release scheduler advisory lock")
        db.close()


async def run_scheduler_loop(stop_event: asyncio.Event) -> None:
    poll_seconds = max(int(os.getenv("SCHEDULED_REPORTS_POLL_SECONDS", "60")), 5)
    while not stop_event.is_set():
        _runtime_status["last_iteration_started_at"] = datetime.now(UTC).isoformat()
        try:
            processed = process_due_report_schedules()
            maybe_run_hosting_monitor_check()
            _runtime_status["last_iteration_processed"] = processed
            _runtime_status["last_iteration_error"] = None
            _runtime_status["consecutive_failures"] = 0
        except Exception as exc:
            logger.exception("Scheduled report loop iteration failed")
            _runtime_status["last_iteration_error"] = f"{exc.__class__.__name__}: {str(exc)}"
            _runtime_status["consecutive_failures"] = int(_runtime_status["consecutive_failures"] or 0) + 1
        finally:
            _runtime_status["last_iteration_completed_at"] = datetime.now(UTC).isoformat()
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=poll_seconds)
