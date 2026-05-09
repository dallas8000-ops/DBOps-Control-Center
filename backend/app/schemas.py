from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


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
    report_key: str
    params: dict[str, Any]
    row_count: int | None
    duration_ms: int | None
    success: bool
    error_message: str | None
    created_at: datetime
    user_email: str


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
