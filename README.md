# DBOps Control Center

Role-based database operations dashboard for small teams that need safe visibility, incident tracking, and audited reporting without exposing raw SQL access to everyone.

## Overview

`DBOps Control Center` is a full-stack portfolio app that demonstrates an operations-focused workflow:

- track incidents and operational summary metrics
- enforce JWT auth + RBAC (`DBA`, `Analyst`, `Viewer`)
- execute only whitelisted read-only SQL reports
- audit report execution history
- manage user lifecycle as a DBA (create, reset password, enable/disable, delete)

This repo is designed to run locally with Docker Compose and deploy to Render with `render.yaml`.

## Completion level (current state)

Overall project completion is approximately **82%** toward a production-ready internal tool.

- **Implemented and working**
  - Authentication + RBAC (`DBA`, `Analyst`, `Viewer`)
  - Auth rate limiting on login endpoints (configurable via env)
  - DBA bootstrap flow for empty database
  - User lifecycle controls (create, reset password, enable/disable, delete)
  - User admin audit log (`GET /auth/users/audit`)
  - Incident create, filtered/list/sort, Analyst/DBA edit (`PATCH /incidents/{id}`), DBA resolve
  - Whitelisted report execution, CSV export, and execution audit trail
  - DBA-managed scheduled reports (daily/weekly UTC) with optional webhook delivery hook
  - Idempotent demo seed (`python -m app` / `seed-demo`)
  - Starter backend pytest suite + frontend smoke tests + CI gates
  - Local Docker Compose workflow and Render deployment path
- **Partially complete**
  - Operational observability (`/health`, scheduler introspection; metrics/tracing not yet added)
  - Incident workflow depth (no per-field history timeline or SLA clocks yet)
  - Scheduled report delivery (email path is a logged placeholder; multi-instance scheduler coordination not solved)
- **Not complete yet**
  - Broad automated coverage (failure paths, schedules, billing hooks if used)
  - SSO/OIDC and hardened production runbooks

## Core capabilities

- **Authentication and RBAC**
  - JWT login with bcrypt-hashed passwords
  - Bootstrap first DBA when DB has no users
  - Role-gated API and UI behavior
  - Disabled users are blocked from authenticated access
  - Centralized frontend 401/disabled-session handling with clear re-login messaging

- **User administration (DBA)**
  - Create users (`DBA`, `Analyst`, `Viewer`)
  - View user directory
  - Reset user password
  - Enable/disable user accounts
  - Delete users (self-protection prevents deleting/disable own account)

- **Incident operations**
  - Create, list with filters (status, severity, owner, search, date range) and sort (`newest` / `oldest` / `severity`)
  - Analyst/DBA update open incidents (`PATCH /incidents/{id}`)
  - DBA resolve workflow (`PATCH /incidents/{id}/resolve`)
  - Operational summary cards (total/open/resolved/high severity)

- **Safe reporting and audit trail**
  - Report catalog defined in code (`backend/app/report_catalog.py`)
  - Parameterized, whitelisted, read-only SQL execution
  - Execution logging to `report_execution_logs`
  - DBA-managed report schedules with daily or weekly UTC run windows
  - Delivery target hooks for scheduled runs (`none`, `email` placeholder logging, `webhook` POST)

- **Deployment readiness**
  - Alembic migrations on startup
  - Docker Compose local stack
  - Render blueprint support (`dbops-db`, `dbops-api`, `dbops-web`)

## Tech stack

- **Backend**: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **Frontend**: React, Vite
- **Auth**: JWT (HS256), passlib/bcrypt
- **Local runtime**: Docker Desktop + Docker Compose

## RBAC matrix

| Capability | Viewer | Analyst | DBA |
|------------|--------|---------|-----|
| `GET /incidents` (filters/sort), `GET /reports/summary` | Yes | Yes | Yes |
| `GET /reports/catalog`, `POST /reports/run`, `POST /reports/export/csv` | Yes (filtered catalog) | Yes | Yes |
| `POST /incidents` | No | Yes | Yes |
| `PATCH /incidents/{id}` (edit fields) | No | Yes | Yes |
| `PATCH /incidents/{id}/resolve` | No | No | Yes |
| User management (`/auth/users*`, `/auth/users/audit`) | No | No | Yes |
| Report schedules (`POST/GET /reports/schedules`, status patch) | No | No | Yes |
| `GET /reports/runs` (audit trail) | No | No | Yes |

## Run locally

### 1) Docker Compose (recommended)

From repo root:

```bash
docker compose up --build
```

Endpoints:

- Frontend: `http://localhost:5173`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

Environment variables (Compose/root `.env`):

- `JWT_SECRET_KEY` — signing secret
- `FRONTEND_ORIGINS` — comma-separated allowed origins
- `AUTH_RATE_LIMIT_MAX_REQUESTS` — max auth requests allowed per IP in window (default: `20`)
- `AUTH_RATE_LIMIT_WINDOW_SECONDS` — auth rate-limit window size in seconds (default: `60`)

> Note: backend image normalizes `entrypoint.sh` line endings during build for Windows compatibility.

### 2) First-time bootstrap

If the database is empty:

1. Open UI
2. Use **First-time setup (bootstrap DBA)**
3. Create first DBA
4. Sign in and create additional accounts

### 3) Seed realistic demo data (idempotent)

From `backend` folder:

```bash
python -m app
```

Equivalent explicit command:

```bash
python -m app seed-demo
```

What gets seeded on each run:

- 3 users: `DBA`, `Analyst`, `Viewer`
- 15 incidents with varied severity/status/owner
- 12 report execution logs (`incidents_by_status`, `incidents_recent`, `open_high_severity`)

Seeded default user emails:

- `barney@example.com` (DBA)
- `analyst@example.com` (Analyst)
- `viewer@example.com` (Viewer)

The seeder is idempotent, so rerunning it updates the same demo records instead of creating duplicates.

Run in Docker Compose:

```bash
docker compose exec backend python -m app
```

## API summary

- **Health**
  - `GET /health`

- **Auth**
  - `POST /auth/register` (bootstrap first DBA only)
  - `POST /auth/login`
  - `POST /auth/token`
  - `GET /auth/me`

- **User administration (DBA)**
  - `GET /auth/users`
  - `GET /auth/users/audit`
  - `POST /auth/users`
  - `PATCH /auth/users/{user_id}/password`
  - `PATCH /auth/users/{user_id}/status`
  - `DELETE /auth/users/{user_id}`

- **Incidents**
  - `GET /incidents` (supports `status`, `severity`, `owner`, `search`, `start_date`, `end_date`, `sort`)
  - `POST /incidents`
  - `PATCH /incidents/{id}`
  - `PATCH /incidents/{id}/resolve`

- **Reports**
  - `GET /reports/summary`
  - `GET /reports/catalog`
  - `POST /reports/run`
  - `POST /reports/export/csv`
  - `GET /reports/runs`
  - `POST /reports/schedules`
  - `GET /reports/schedules`
  - `PATCH /reports/schedules/{schedule_id}/status`

## Scheduled report MVP notes

- Schedules run inside the API process on a simple polling loop.
- Supported cadences are `daily` and `weekly`, using UTC hour/minute fields.
- Scheduled executions reuse the same whitelisted report validation and write into `report_execution_logs`.
- Delivery configuration supports `none`, `email`, and `webhook` targets.
- Failures are stored on the schedule (`last_error`) and also logged as failed report executions.
- Email delivery is a hook placeholder that logs notification payloads for operator wiring.
- Webhook delivery sends a JSON payload with short timeout and logs delivery errors without blocking scheduler progress.
- Known limitation: this is a single-process scheduler. If you run multiple API instances, each instance can attempt the same due schedule unless you add external coordination.
- Known limitation: schedules are owned by the creating DBA account. If that user is disabled, the schedule remains enabled but future runs log a failure until the owner is re-enabled or the schedule is replaced.

## Commercial assets package

- Pricing sheet: `docs/commercial-assets/pricing-sheet.md`
- Onboarding checklist: `docs/commercial-assets/onboarding-checklist-day0-day7.md`
- Support SLA matrix: `docs/commercial-assets/support-sla-response-matrix.md`
- Demo scripts: `docs/commercial-assets/demo-video-scripts.md`

## Testing and validation status

### Latest verified checks

| Area | Test / Validation | Status |
|------|-------------------|--------|
| Frontend build | `npm run build` | ✅ Passing |
| Frontend smoke tests | `npm run test:run` | ✅ Passing (4 smoke tests) |
| Frontend lint health | IDE lint diagnostics on edited files | ✅ Passing |
| Docker local stack | `docker compose up --build` | ✅ Passing |
| Backend migration chain | Alembic upgrades through head (e.g. `007_billing_and_onboarding`) | ✅ Passing |
| Backend integration tests | `pytest -q` (auth/RBAC + incident/filter + auth-rate-limit + admin-audit coverage) | ✅ Passing (14 tests) |
| API health | `GET /health` | ✅ Passing |
| Auth smoke tests | Bootstrap/login/create-user/manual role checks | ✅ Passing |
| DBA admin actions | Reset password, enable/disable, delete user (manual) | ✅ Passing |

### Test gaps (planned)

- ⚠️ Backend suite covers core paths; expand coverage for schedules, CSV export edge cases, and billing/admin routes if used in production
- ⚠️ Frontend smoke tests are starter-level; add deeper integration or Playwright/Cypress flows when UI stabilizes
- ⚠️ Optional CI hardening: migration drift checks, coverage thresholds, dependency audit gates

### Local quality checks

Backend:

```bash
cd backend
pytest -q
```

Frontend:

```bash
cd frontend
npm run lint
npm run test:run
npm run build
```

## Render deployment

1. Connect repo and deploy with `render.yaml` (Blueprint), or create services manually.
2. **API service**
   - Docker from `backend/Dockerfile`
   - `DATABASE_URL` from Render Postgres
   - `JWT_SECRET_KEY` set/generated
   - `FRONTEND_ORIGINS` set to static-site origin(s)
3. **Web service**
   - Static site from `frontend`
   - Build: `npm install && npm run build`
   - Publish: `dist`
   - Set `VITE_API_URL` before build (baked into bundle)

If Postgres requires SSL, append params to `DATABASE_URL` (commonly `?sslmode=require`).

## Planned updates (next phase)

Target window: **~2 weeks** (items below are **not** duplicates of what is already shipped in this repo).

1. **Workflow and product depth**
   - Incident change history / timeline (who changed what, when)
   - SLA-style targets or escalation states (beyond open/resolved)
   - Optional “wipe demo data” / tenant reset helper aligned with seed script

2. **Reporting and scheduler production readiness**
   - Distributed-safe scheduling (single-leader or external worker; avoid duplicate runs across API replicas)
   - Real SMTP or provider integration for email delivery (replace placeholder logging)
   - Report retention policies and export archival

3. **Quality and observability**
   - Expand pytest coverage on scheduler, webhooks, and failure branches
   - Add structured logging + request correlation IDs
   - Metrics (latency, auth failures, schedule failures) or lightweight OpenTelemetry hooks

4. **Enterprise hardening**
   - SSO/OIDC option for larger tenants
   - Rate limiting beyond auth endpoints where appropriate
   - Expanded operations runbook (`docs/`) for Render + incident response
