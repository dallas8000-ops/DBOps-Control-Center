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
