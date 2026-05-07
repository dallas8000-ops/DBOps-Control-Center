import json
import os

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth_utils import create_access_token, hash_password, verify_password
from .db import engine, get_db
from .deps import get_current_user, require_roles
from .models import Incident, ReportExecutionLog, User
from .report_catalog import REPORTS
from .report_runner import execute_whitelisted_report
from .schemas import (
    IncidentCreate,
    IncidentRead,
    LoginRequest,
    ReportCatalogEntry,
    ReportExecuteRequest,
    ReportExecuteResponse,
    ReportParamSpec,
    ReportRunRead,
    Token,
    UserCreate,
    UserRead,
)

app = FastAPI(title="DBOps Control Center API", version="0.3.1")


def _parse_cors_origins(raw: str | None) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    for part in raw.replace("\r", "").split(","):
        o = part.strip().strip('"').strip("'").rstrip("/")
        if o:
            out.append(o)
    return out


_frontend_origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").strip()
_parsed_origins = _parse_cors_origins(_frontend_origins)
allow_origins = _parsed_origins if _parsed_origins else ["http://localhost:5173"]

_cors_kw: dict = {
    "allow_origins": allow_origins,
    "allow_credentials": False,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
# Lets any *.onrender.com static site call this API (JWT still required for protected routes).
if os.getenv("CORS_DISABLE_RENDER_REGEX", "").lower() not in ("1", "true", "yes"):
    _cors_kw["allow_origin_regex"] = r"^https://[a-zA-Z0-9\-]+\.onrender\.com$"

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


@app.post("/auth/login", response_model=Token)
def login_json(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=token)


@app.post("/auth/token", response_model=Token)
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username.lower()).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=token)


@app.get("/auth/me", response_model=UserRead)
def me(current: User = Depends(get_current_user)):
    return current


@app.post("/auth/register", response_model=UserRead, status_code=201)
def register_bootstrap(payload: UserCreate, db: Session = Depends(get_db)):
    """First user only (role must be DBA). Further accounts use POST /auth/users as DBA."""
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


@app.post("/auth/users", response_model=UserRead, status_code=201)
def register_as_dba(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("DBA")),
):
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


@app.get("/incidents", response_model=list[IncidentRead])
def list_incidents(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("DBA", "Analyst", "Viewer")),
):
    return db.query(Incident).order_by(Incident.created_at.desc()).all()


@app.post("/incidents", response_model=IncidentRead, status_code=201)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("DBA", "Analyst")),
):
    incident = Incident(
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        owner=payload.owner,
        status="open",
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@app.patch("/incidents/{incident_id}/resolve", response_model=IncidentRead)
def resolve_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("DBA")),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident.status = "resolved"
    db.commit()
    db.refresh(incident)
    return incident


@app.get("/reports/catalog", response_model=list[ReportCatalogEntry])
def report_catalog(current: User = Depends(get_current_user)):
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


@app.post("/reports/run", response_model=ReportExecuteResponse)
def run_report(
    body: ReportExecuteRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    try:
        data = execute_whitelisted_report(db, current, body.report_key, body.params)
        return ReportExecuteResponse.model_validate(data)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Insufficient permissions for this report")
    except ValueError as exc:
        msg = str(exc)
        code = 404 if msg.startswith("Unknown report:") else 400
        raise HTTPException(status_code=code, detail=msg)


@app.get("/reports/runs", response_model=list[ReportRunRead])
def list_report_runs(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("DBA")),
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


@app.get("/reports/summary")
def report_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("DBA", "Analyst", "Viewer")),
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
