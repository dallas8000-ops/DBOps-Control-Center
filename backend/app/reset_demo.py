"""Clear operational demo data while keeping user accounts and billing rows."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Incident, IncidentHistory, OnboardingEvent, ReportExecutionLog, ReportSchedule


def reset_demo_data() -> dict[str, int]:
    """Delete incidents (and history), report logs, schedules, onboarding markers."""
    db: Session = SessionLocal()
    try:
        counts = {
            "incident_history": db.query(IncidentHistory).delete(synchronize_session=False),
            "incidents": db.query(Incident).delete(synchronize_session=False),
            "report_execution_logs": db.query(ReportExecutionLog).delete(synchronize_session=False),
            "report_schedules": db.query(ReportSchedule).delete(synchronize_session=False),
            "onboarding_events": db.query(OnboardingEvent).delete(synchronize_session=False),
        }
        db.commit()
        return counts
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
