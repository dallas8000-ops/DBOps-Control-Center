import asyncio
import json
import logging
import os
from contextlib import suppress
from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from .db import SessionLocal
from .models import ReportExecutionLog, ReportSchedule, User
from .report_runner import execute_whitelisted_report, prepare_report_request

logger = logging.getLogger(__name__)


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


def process_due_report_schedules(session_factory: sessionmaker = SessionLocal, now: datetime | None = None) -> int:
    processed = 0
    run_at = now or datetime.utcnow()
    db = session_factory()
    try:
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
                try:
                    params = json.loads(schedule.params_json)
                except json.JSONDecodeError:
                    params = {}
                    error_message = "Schedule parameters are invalid JSON"
                if error_message is None:
                    try:
                        prepare_report_request(owner, schedule.report_key, params)
                        execute_whitelisted_report(
                            db,
                            owner,
                            schedule.report_key,
                            params,
                            scheduled_report_id=schedule.id,
                        )
                    except (PermissionError, ValueError) as exc:
                        error_message = str(exc)
                    except Exception as exc:
                        error_message = str(exc)

            schedule.last_run_at = run_at
            schedule.next_run_at = next_run_at
            if error_message is None:
                schedule.last_success_at = run_at
                schedule.last_error = None
            else:
                schedule.last_error = error_message[:4000]
                _log_schedule_failure(db, schedule, schedule.created_by_user_id, error_message, run_at)
            db.add(schedule)
            db.commit()
            processed += 1
        return processed
    finally:
        db.close()


async def run_scheduler_loop(stop_event: asyncio.Event) -> None:
    poll_seconds = max(int(os.getenv("SCHEDULED_REPORTS_POLL_SECONDS", "60")), 5)
    while not stop_event.is_set():
        try:
            process_due_report_schedules()
        except Exception:
            logger.exception("Scheduled report loop iteration failed")
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=poll_seconds)
