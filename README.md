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

Overall project completion is approximately **75%** toward a production-ready internal tool.

- **Implemented and working**
  - Authentication + RBAC (`DBA`, `Analyst`, `Viewer`)
  - DBA bootstrap flow for empty database
  - User lifecycle controls (create, reset password, enable/disable, delete)
  - Incident create/list/resolve workflow
  - Whitelisted report execution + report audit trail
  - Scheduled report definitions, enable/disable controls, and automatic execution logging
  - Local Docker Compose workflow and Render deployment path
- **Partially complete**
  - Operational observability (basic health checks are present; deeper metrics/tracing not yet added)
  - Incident workflow depth (history/SLA workflow not yet added)
  - Reporting UX (scheduling not yet added)
- **Not complete yet**
  - Full automated test suite and CI quality gates
  - Advanced production controls (rate limiting, SSO, full runbooks)

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
  - Create, list, and resolve incidents with ownership and severity
  - Operational summary cards (total/open/resolved/high severity)

- **Safe reporting and audit trail**
  - Report catalog defined in code (`backend/app/report_catalog.py`)
  - Parameterized, whitelisted, read-only SQL execution
  - Execution logging to `report_execution_logs`
  - DBA-managed report schedules with daily or weekly UTC run windows

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
| `GET /incidents`, `GET /reports/summary` | Yes | Yes | Yes |
| `GET /reports/catalog`, `POST /reports/run`, `POST /reports/export/csv` | Yes (filtered catalog) | Yes | Yes |
| `POST /incidents` | No | Yes | Yes |
| `PATCH /incidents/{id}/resolve` | No | No | Yes |
| User management (`/auth/users*`) | No | No | Yes |
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
- Failures are stored on the schedule (`last_error`) and also logged as failed report executions.
- Known limitation: this is a single-process scheduler. If you run multiple API instances, each instance can attempt the same due schedule unless you add external coordination.
- Known limitation: schedules are owned by the creating DBA account. If that user is disabled, the schedule remains enabled but future runs log a failure until the owner is re-enabled or the schedule is replaced.

## Testing and validation status

### Latest verified checks

| Area | Test / Validation | Status |
|------|-------------------|--------|
| Frontend build | `npm run build` | ✅ Passing |
| Frontend smoke tests | `npm run test:run` | ✅ Passing (4 smoke tests) |
| Frontend lint health | IDE lint diagnostics on edited files | ✅ Passing |
| Docker local stack | `docker compose up --build` | ✅ Passing |
| Backend migration chain | Alembic upgrades through `003_users_active` | ✅ Passing |
| Backend integration tests | `pytest -q` (auth/RBAC + incident/filter + auth-rate-limit + admin-audit coverage) | ✅ Passing (14 tests) |
| API health | `GET /health` | ✅ Passing |
| Auth smoke tests | Bootstrap/login/create-user/manual role checks | ✅ Passing |
| DBA admin actions | Reset password, enable/disable, delete user (manual) | ✅ Passing |

### Test gaps (planned)

- ⚠️ Backend suite is still starter-level and needs broader endpoint and failure-path coverage
- ⚠️ Frontend smoke tests are in place, but deeper integration/e2e coverage is still pending
- ⚠️ CI fail gates are active; migration checks and stricter quality policies can be added next

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

Target window: **2 weeks**

1. **Data and workflow**
   - Incident edit + filter/search/sort
   - Demo data seeding polish and reset flow
2. **Quality and reliability**
   - Backend integration tests for auth/RBAC and critical endpoints
   - Frontend smoke/integration tests for login and DBA flows
   - CI checks for build/lint/test
3. **Reporting and operations**
  - Scheduled report runs with execution controls
   - User admin action audit trail improvements
   - Expanded troubleshooting/runbook documentation
