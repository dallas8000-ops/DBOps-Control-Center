# DBOps Control Center

[![CI](https://github.com/dallas8000-ops/DBOps-Control-Center/actions/workflows/ci.yml/badge.svg)](https://github.com/dallas8000-ops/DBOps-Control-Center/actions/workflows/ci.yml)

**Private / proprietary.** This project is maintained in a **private** repository. **Sale, redistribution, download for others, or disclosure of this codebase or related materials without the copyright owner’s express written consent is prohibited.** See [`LEGAL_NOTICE.md`](./LEGAL_NOTICE.md) for the full notice.

Commercial terms: [`DBOps_LICENSE.md`](./DBOps_LICENSE.md). Product positioning and pitch: [`DBOps_Product_Positioning.md`](./DBOps_Product_Positioning.md).

Role-based database operations dashboard for small teams that need safe visibility, incident tracking, and audited reporting without exposing raw SQL access to everyone.

## Overview

`DBOps Control Center` is a full-stack portfolio app that demonstrates an operations-focused workflow:

- track incidents (including change audit history), and operational summary metrics
- enforce JWT auth + RBAC (`DBA`, `Analyst`, `Viewer`)
- execute only whitelisted read-only SQL reports
- audit report execution history
- manage user lifecycle as a DBA (create, reset password, enable/disable, delete)

This repo is designed to run locally with Docker Compose and deploy to Render with `render.yaml`.

## Completion level (current state)

Overall project completion is approximately **87%** toward a production-ready internal tool.

- **Implemented and working**
  - Authentication + RBAC (`DBA`, `Analyst`, `Viewer`)
  - Auth rate limiting on login endpoints (configurable via env)
  - **API rate limiting** (per-IP) on high-cost routes: incident create, report run, CSV export (`API_RATE_LIMIT_*` env)
  - **Request correlation**: `X-Request-ID` header + structured access lines (`dbops.access` logger)
  - DBA bootstrap flow for empty database
  - User lifecycle controls (create, reset password, enable/disable, delete)
  - User admin audit log (`GET /auth/users/audit`)
  - Incident create, filtered/list/sort, optional **`due_at`** and **`overdue=true`** filter (open + past due), Analyst/DBA edit, DBA resolve
  - **Audit history** (`GET /incidents/{id}/history`, CSV export, in-app History + **History CSV**)
  - Whitelisted report execution, CSV export, and execution audit trail; optional **report log retention** purge (`REPORT_EXECUTION_LOG_RETENTION_DAYS`)
  - DBA-managed scheduled reports (daily/weekly UTC) with **`none` / `email` (SMTP when configured)** / `webhook` delivery
  - **PostgreSQL advisory lock** so only one API replica runs the due-schedule sweep per tick (no paid coordinator)
  - Idempotent demo seed (`python -m app` / `seed-demo`) and **`python -m app reset-demo --yes`** (clears operational data; keeps users/billing)
  - Backend pytest suite + frontend smoke tests + CI gates
  - Local Docker Compose workflow and Render deployment path
- **Partially complete**
  - Operational observability (access log + request ID; no full metrics/tracing stack yet)
  - Incident workflow (due dates shipped; **no** comments thread, attachments, or formal escalation states yet)
  - Scheduler production hardening beyond Postgres locking (e.g. external worker / Redis lease) if you outgrow the current pattern
- **Not complete yet**
  - Broad automated coverage (failure paths, billing edge cases if used in production)
  - SSO/OIDC and expanded production runbooks

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
  - Create, list with filters (status, severity, owner, search, date range, **`overdue`** for open items past **`due_at`**) and sort (`newest` / `oldest` / `severity`)
  - Optional **target due** (`due_at`) on create/edit; Analyst/DBA updates logged with before/after field diffs
  - DBA resolve workflow; resolve events logged (idempotent if already resolved)
  - **History**: chronological `created` / `updated` / `resolved`; JSON in API; **CSV export**; dashboard **History** + **History CSV**
  - Operational summary cards (total/open/resolved/high severity)

- **Safe reporting and audit trail**
  - Report catalog defined in code (`backend/app/report_catalog.py`)
  - Parameterized, whitelisted, read-only SQL execution (**rate-limited** per IP on run + CSV export)
  - Execution logging to `report_execution_logs` (optional **retention** purge via env)
  - DBA-managed report schedules with daily or weekly UTC run windows
  - Delivery: `none`, **`email` via optional SMTP env** (stdlib; no vendor SDK required), or `webhook` POST

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
| `GET /incidents/{id}/history` (audit trail), `GET /incidents/{id}/history/export` (CSV) | Yes | Yes | Yes |
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

To **clear operational demo data** (incidents, history, report logs, schedules, onboarding markers) while **keeping users and billing**, use:

```bash
python -m app reset-demo --yes
```

What gets seeded on each run:

- 3 users: `DBA`, `Analyst`, `Viewer`
- 15 incidents with varied severity/status/owner
- 12 report execution logs (`incidents_by_status`, `incidents_recent`, `open_high_severity`)

Seeded incidents have **no** `incident_history` rows (history is recorded for activity after migration `008_incident_history` is applied).

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
  - `GET /incidents` (supports `status`, `severity`, `owner`, `search`, `start_date`, `end_date`, `sort`, **`overdue`**)
  - `GET /incidents/{id}/history` (chronological audit: create, field updates, resolve)
  - `GET /incidents/{id}/history/export` (CSV download)
  - `POST /incidents` (optional `due_at`; rate-limited per IP)
  - `PATCH /incidents/{id}` (optional `due_at` updates)
  - `PATCH /incidents/{id}/resolve`

- **Reports**
  - `GET /reports/summary`
  - `GET /reports/catalog`
  - `POST /reports/run` (rate-limited per IP)
  - `POST /reports/export/csv` (rate-limited per IP)
  - `GET /reports/runs`
  - `POST /reports/schedules`
  - `GET /reports/schedules`
  - `PATCH /reports/schedules/{schedule_id}/status`

Protected routes accept `Authorization: Bearer …`. Responses include **`X-Request-ID`** (or echo a client-provided `X-Request-ID`). See `backend/.env.example` for **`API_RATE_LIMIT_*`**, **SMTP_***, **`REPORT_EXECUTION_LOG_RETENTION_DAYS`**, etc.

## Scheduled report MVP notes

- Schedules run inside the API process on a simple polling loop.
- Supported cadences are `daily` and `weekly`, using UTC hour/minute fields.
- Scheduled executions reuse the same whitelisted report validation and write into `report_execution_logs`.
- Delivery configuration supports `none`, **`email` (sent via stdlib SMTP when `SMTP_HOST` and related env vars are set; otherwise log-only)**, and `webhook` targets.
- Failures are stored on the schedule (`last_error`) and also logged as failed report executions.
- Webhook delivery sends a JSON payload with short timeout and logs delivery errors without blocking scheduler progress.
- **Multi-instance APIs (PostgreSQL):** a **session advisory lock** ensures only one replica processes due schedules per tick. SQLite / tests skip locking.
- Optional: **`REPORT_EXECUTION_LOG_RETENTION_DAYS`** prunes old execution log rows at the start of a scheduler tick (leader only on Postgres).
- Known limitation: schedules are owned by the creating DBA account. If that user is disabled, the schedule remains enabled but future runs log a failure until the owner is re-enabled or the schedule is replaced.

## Commercial assets package

- **Proprietary notice / redistribution:** [`LEGAL_NOTICE.md`](./LEGAL_NOTICE.md)
- Pricing sheet: `docs/commercial-assets/pricing-sheet.md`
- Source license + product outline (template): `docs/commercial-assets/source-license-product-outline.md`
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
| Backend migration chain | Alembic upgrades through head (includes `009_incident_due_at`) | ✅ Passing |
| Backend integration tests | `pytest -q` (auth/RBAC, incidents, history, CSV, rate limits, schedules, billing paths, etc.) | ✅ Passing (32 tests) |
| API health | `GET /health` | ✅ Passing |
| Auth smoke tests | Bootstrap/login/create-user/manual role checks | ✅ Passing |
| DBA admin actions | Reset password, enable/disable, delete user (manual) | ✅ Passing |

### Test gaps (planned)

- ⚠️ Backend suite covers core paths including incident history; expand coverage for schedules, CSV export edge cases, and billing/admin routes if used in production
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

### CI quality gates

GitHub Actions workflow: `.github/workflows/ci.yml`

The CI pipeline runs on push and pull requests to `main`/`master` with three required jobs:

- `backend`: installs backend deps, runs `ruff` critical checks, then `pytest -q`
- `frontend`: runs `npm ci`, `npm run lint`, `npm run test:run`, and `npm run build`
- `migration_sanity`: starts PostgreSQL and runs `alembic upgrade head` with CI `DATABASE_URL`

Recommended branch protection for production safety:

- Require all status checks from `CI` workflow before merge
- Require pull request reviews before merge

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
   - Formal escalation states or SLA policies beyond optional `due_at` / overdue filter
   - Richer incident timeline (comments, attachments)
   - Optional “wipe demo data” is available via `reset-demo`; consider a **DBA-only HTTP** helper behind env if you want it in the UI

2. **Reporting and scheduler production readiness**
   - External worker or stronger lease pattern if you outgrow Postgres advisory locking
   - Report retention policies beyond execution-log pruning (e.g. CSV archival to object storage)

3. **Quality and observability**
   - Expand pytest coverage on webhooks, SMTP failure paths, and billing edge cases
   - Metrics (latency, schedule failures) or lightweight OpenTelemetry hooks (self-hosted or your existing stack)

4. **Enterprise hardening**
   - SSO/OIDC option for larger tenants
   - Rate limiting beyond selected routes where appropriate
   - Expanded operations runbook (`docs/`) for Render + incident response

## Branch Protection Rules

This repository does not currently have branch protection rules configured, as it is maintained by a single developer. However, if this repository is transferred to a team or organization, it is recommended to configure branch protection rules to ensure code quality and prevent accidental changes to critical branches.

### Suggested Branch Protection Settings:
1. **Require a pull request before merging**:
   - Require at least one approval.
   - Dismiss stale pull request approvals when new commits are pushed.
2. **Require status checks to pass before merging**:
   - Ensure all CI/CD checks pass before merging.
3. **Restrict who can push to matching branches**:
   - Limit push access to specific team members or roles.

For more information, refer to the [GitHub documentation on branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-protected-branches).
