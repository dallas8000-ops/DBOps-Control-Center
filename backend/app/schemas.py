from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, model_validator


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(DBA|Analyst|Viewer)$")


class UserRead(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)
    severity: str = Field(default="medium")
    owner: str = Field(default="unassigned")


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=5)
    severity: str | None = None
    owner: str | None = Field(default=None, min_length=1, max_length=120)


class IncidentRead(BaseModel):
    id: int
    title: str
    description: str
    status: str
    severity: str
    owner: str
    created_at: datetime

    class Config:
        from_attributes = True


class IncidentHistoryRead(BaseModel):
    id: int
    incident_id: int
    actor_email: str | None
    action: str
    details: dict[str, Any]
    created_at: datetime


class ReportParamSpec(BaseModel):
    name: str
    type: str
    default: int | None = None
    min: int | None = None
    max: int | None = None


class ReportCatalogEntry(BaseModel):
    key: str
    title: str
    description: str
    params: list[ReportParamSpec]


class ReportExecuteRequest(BaseModel):
    report_key: str = Field(min_length=1, max_length=120)
    params: dict[str, Any] | None = None


class ReportExecuteResponse(BaseModel):
    report_key: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    duration_ms: int


class ReportRunRead(BaseModel):
    id: int
    scheduled_report_id: int | None = None
    report_key: str
    params: dict[str, Any]
    row_count: int | None
    duration_ms: int | None
    success: bool
    error_message: str | None
    created_at: datetime
    user_email: str


class ReportScheduleCreate(BaseModel):
    report_key: str = Field(min_length=1, max_length=120)
    params: dict[str, Any] | None = None
    cadence: str = Field(pattern="^(daily|weekly)$")
    weekday_utc: int | None = Field(default=None, ge=0, le=6)
    run_hour_utc: int = Field(ge=0, le=23)
    run_minute_utc: int = Field(ge=0, le=59)
    delivery_kind: str = Field(default="none", pattern="^(none|email|webhook)$")
    delivery_target: str | None = Field(default=None, max_length=320)
    notify_on_success: bool = False
    notify_on_failure: bool = True

    @model_validator(mode="after")
    def validate_weekday(self):
        if self.cadence == "weekly" and self.weekday_utc is None:
            raise ValueError("weekday_utc is required for weekly schedules")
        if self.cadence == "daily":
            self.weekday_utc = None
        if self.delivery_kind != "none" and not self.delivery_target:
            raise ValueError("delivery_target is required when delivery_kind is not none")
        if self.delivery_kind == "none":
            self.delivery_target = None
        return self


class ReportScheduleStatusUpdate(BaseModel):
    is_enabled: bool


class ReportScheduleRead(BaseModel):
    id: int
    report_key: str
    params: dict[str, Any]
    cadence: str
    weekday_utc: int | None
    run_hour_utc: int
    run_minute_utc: int
    delivery_kind: str
    delivery_target: str | None
    notify_on_success: bool
    notify_on_failure: bool
    is_enabled: bool
    next_run_at: datetime
    last_run_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    created_at: datetime
    created_by_user_id: int
    created_by_email: str


class UserPasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserAdminAuditRead(BaseModel):
    id: int
    actor_user_id: int | None
    actor_email: str | None
    target_user_id: int | None
    target_email: str
    action: str
    details: dict[str, Any]
    created_at: datetime


class BillingSettingsRead(BaseModel):
    id: int
    plan_key: str
    billing_status: str
    monthly_price_cents: int
    max_users: int
    max_schedules: int
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BillingSettingsUpdate(BaseModel):
    plan_key: str = Field(min_length=2, max_length=80)
    billing_status: str = Field(min_length=2, max_length=40)
    monthly_price_cents: int = Field(ge=0, le=5_000_000)
    max_users: int = Field(ge=1, le=10_000)
    max_schedules: int = Field(ge=1, le=10_000)
    stripe_customer_id: str | None = Field(default=None, max_length=120)
    stripe_subscription_id: str | None = Field(default=None, max_length=120)


class BillingCheckoutSessionCreate(BaseModel):
    price_id: str | None = Field(default=None, min_length=3, max_length=120)
    plan_key: str | None = Field(default=None, min_length=2, max_length=80)
    success_url: str = Field(min_length=8, max_length=512)
    cancel_url: str = Field(min_length=8, max_length=512)


class BillingCheckoutSessionRead(BaseModel):
    session_id: str
    url: str


class StripeWebhookEventRead(BaseModel):
    received: bool
    event_type: str
    billing_status: str


class OnboardingItemRead(BaseModel):
    key: str
    label: str
    completed: bool
    completed_at: datetime | None


class AdminMetricsRead(BaseModel):
    total_users: int
    active_users: int
    open_incidents: int
    resolved_incidents: int
    enabled_schedules: int
    report_runs_last_24h: int
    successful_report_runs_last_24h: int
    onboarding_completed_steps: int
    onboarding_total_steps: int


class PlanUsageRead(BaseModel):
    user_slots_used: int
    user_slots_remaining: int
    users_at_limit: bool
    schedule_slots_used: int
    schedule_slots_remaining: int
    schedules_at_limit: bool


class ActivityTrendPointRead(BaseModel):
    day: str
    label: str
    incidents_created: int
    report_runs: int
    schedules_created: int


class AdminOverviewRead(BaseModel):
    metrics: AdminMetricsRead
    billing: BillingSettingsRead
    plan_usage: PlanUsageRead
    onboarding: list[OnboardingItemRead]
    activity_trend: list[ActivityTrendPointRead]
