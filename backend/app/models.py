from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


USERS_ID_FK = "users.id"
REPORT_SCHEDULES_ID_FK = "report_schedules.id"
ON_DELETE_SET_NULL = "SET NULL"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="Viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open")
    severity: Mapped[str] = mapped_column(String(50), default="medium")
    owner: Mapped[str] = mapped_column(String(120), default="unassigned")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class IncidentHistory(Base):
    __tablename__ = "incident_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(USERS_ID_FK, ondelete=ON_DELETE_SET_NULL),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ReportSchedule(Base):
    __tablename__ = "report_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(USERS_ID_FK, ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_key: Mapped[str] = mapped_column(String(120), nullable=False)
    params_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    cadence: Mapped[str] = mapped_column(String(20), nullable=False)
    weekday_utc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    run_hour_utc: Mapped[int] = mapped_column(Integer, nullable=False)
    run_minute_utc: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    delivery_target: Mapped[str | None] = mapped_column(String(320), nullable=True)
    notify_on_success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notify_on_failure: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ReportExecutionLog(Base):
    __tablename__ = "report_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(USERS_ID_FK, ondelete="CASCADE"), nullable=False)
    scheduled_report_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(REPORT_SCHEDULES_ID_FK, ondelete=ON_DELETE_SET_NULL),
        nullable=True,
        index=True,
    )
    report_key: Mapped[str] = mapped_column(String(120), nullable=False)
    params_json: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserAdminAuditLog(Base):
    __tablename__ = "user_admin_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(USERS_ID_FK, ondelete=ON_DELETE_SET_NULL),
        nullable=True,
        index=True,
    )
    target_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(USERS_ID_FK, ondelete=ON_DELETE_SET_NULL),
        nullable=True,
        index=True,
    )
    target_email: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class BillingSettings(Base):
    __tablename__ = "billing_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    plan_key: Mapped[str] = mapped_column(String(80), nullable=False, default="starter")
    billing_status: Mapped[str] = mapped_column(String(40), nullable=False, default="trialing")
    monthly_price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=14900)
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_schedules: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OnboardingEvent(Base):
    __tablename__ = "onboarding_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(USERS_ID_FK, ondelete=ON_DELETE_SET_NULL),
        nullable=True,
        index=True,
    )
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
