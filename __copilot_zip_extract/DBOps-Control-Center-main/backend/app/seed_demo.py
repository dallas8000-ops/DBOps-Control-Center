from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth_utils import hash_password
from .db import SessionLocal
from .models import Incident, ReportExecutionLog, User
from .report_catalog import get_report

SEED_FILE = Path(__file__).parent.parent / "seed_data.json"


def _derived_seed_password(role: str) -> str:
    digest = sha256(f"{role}:{os.getenv('SEED_PASSWORD_SALT', 'dbops-local-seed')}".encode("utf-8")).hexdigest()
    return f"{role}-{digest[:14]}!"


def _load_seed_file() -> dict:
    if not SEED_FILE.exists():
        raise FileNotFoundError(
            f"seed_data.json not found at {SEED_FILE}\n"
            "Create it from the template: backend/seed_data.json"
        )
    with SEED_FILE.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    data.pop("_instructions", None)
    return data


def _resolve_password(user_def: dict) -> str:
    env_key = user_def.get("password_env", "")
    if env_key:
        val = os.getenv(env_key)
        if val:
            return val
    return _derived_seed_password(user_def["role"].lower())


def _upsert_user(db: Session, *, email: str, role: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.lower()).first()
    if user is None:
        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.flush()
        return user

    if user.role != role:
        user.role = role
    if not user.is_active:
        user.is_active = True
    db.add(user)
    return user


def _upsert_incident(db: Session, payload: dict) -> Incident:
    title = payload["title"]
    created_at = datetime.fromisoformat(payload["created_at"]) if payload.get("created_at") else datetime.now(timezone.utc).replace(tzinfo=None)
    due_at_val = datetime.fromisoformat(str(payload["due_at"])) if payload.get("due_at") else None
    incident = db.query(Incident).filter(Incident.title == title).first()
    if incident is None:
        incident = Incident(
            title=title,
            description=payload.get("description", ""),
            status=payload.get("status", "open"),
            severity=payload.get("severity", "medium"),
            owner=payload.get("owner", "unassigned"),
            created_at=created_at,
            due_at=due_at_val,
        )
        db.add(incident)
        return incident

    incident.description = payload.get("description", incident.description)
    incident.status = payload.get("status", incident.status)
    incident.severity = payload.get("severity", incident.severity)
    incident.owner = payload.get("owner", incident.owner)
    incident.created_at = created_at
    if "due_at" in payload:
        incident.due_at = due_at_val if payload.get("due_at") else None
    db.add(incident)
    return incident


def _measure_report(db: Session, report_key: str, params: dict) -> tuple[int | None, int, bool, str | None]:
    spec = get_report(report_key)
    if spec is None:
        return None, 0, False, f"Unknown report key: {report_key}"

    started = time.perf_counter()
    try:
        rows = db.execute(text(spec["sql"].strip()), params).mappings().all()
        duration_ms = int((time.perf_counter() - started) * 1000)
        return len(rows), duration_ms, True, None
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return None, duration_ms, False, str(exc)[:4000]


def _upsert_report_log(
    db: Session,
    *,
    user_id: int,
    report_key: str,
    params: dict,
    row_count: int | None,
    duration_ms: int,
    success: bool,
    error_message: str | None,
    created_at: datetime,
) -> None:
    existing = (
        db.query(ReportExecutionLog)
        .filter(
            ReportExecutionLog.user_id == user_id,
            ReportExecutionLog.report_key == report_key,
            ReportExecutionLog.created_at == created_at,
        )
        .first()
    )
    params_json = json.dumps(params, sort_keys=True)
    if existing is None:
        log = ReportExecutionLog(
            user_id=user_id,
            report_key=report_key,
            params_json=params_json,
            row_count=row_count,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            created_at=created_at,
        )
        db.add(log)
    else:
        existing.params_json = params_json
        existing.row_count = row_count
        existing.duration_ms = duration_ms
        existing.success = success
        existing.error_message = error_message
        db.add(existing)


def seed_demo_data() -> None:
    data = _load_seed_file()
    db = SessionLocal()
    try:
        # ── Users ─────────────────────────────────────────────────────────────
        user_map: dict[str, User] = {}
        for user_def in data.get("users", []):
            user_def.pop("note", None)
            email = user_def["email"]
            role = user_def["role"]
            password = _resolve_password(user_def)
            user = _upsert_user(db, email=email, role=role, password=password)
            user_map[email] = user
            print(f"  user  {email} ({role})")
        db.flush()

        # ── Incidents ──────────────────────────────────────────────────────────
        for item in data.get("incidents", []):
            item.pop("_hint", None)
            if not item.get("title"):
                print("  [skip] incident with empty title")
                continue
            _upsert_incident(db, item)
            print(f"  incident  {item['title']}")

        db.flush()

        # ── Report logs ────────────────────────────────────────────────────────
        for item in data.get("report_logs", []):
            email = item["user_email"]
            user = user_map.get(email) or db.query(User).filter(User.email == email.lower()).first()
            if user is None:
                print(f"  [skip] report log — user not found: {email}")
                continue
            report_key = item["report_key"]
            params = item.get("params", {})
            run_at = datetime.fromisoformat(item["run_at"]) if item.get("run_at") else datetime.now(timezone.utc).replace(tzinfo=None)
            row_count, duration_ms, success, error_message = _measure_report(db, report_key, params)
            _upsert_report_log(
                db,
                user_id=user.id,
                report_key=report_key,
                params=params,
                row_count=row_count,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
                created_at=run_at,
            )
            print(f"  report log  {report_key} → {email} @ {run_at.date()}")

        db.commit()

        n_users = len(data.get("users", []))
        n_incidents = len([i for i in data.get("incidents", []) if i.get("title")])
        n_logs = len(data.get("report_logs", []))
        print(f"\nSeed complete — users: {n_users}  incidents: {n_incidents}  report_logs: {n_logs}")
        print(f"Data source: {SEED_FILE}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()