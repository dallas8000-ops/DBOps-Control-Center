# DBOps Control Center — Sprint Board

**Trello:** [dbops-control-center](https://trello.com/b/s7LuzRWy/dbops-control-center)  
**Sync (optional):** `python scripts/trello_sync.py` with `TRELLO_*` in `.env`

---

## Current batch — Week 6 (Stripe ops)

### FEATURE: Stripe billing integration wiring
**Labels:** `backend` `frontend` `high-priority`

**Description:** Wire billing scaffolding to Stripe checkout + webhook lifecycle for event-driven plan state.

**Checklist:**
- [x] Create feature branch from `main`: `feature/stripe-billing-wiring`
- [x] Add backend endpoint `POST /billing/checkout/session` (DBA)
- [x] Add backend endpoint `POST /billing/webhook` with Stripe signature verification
- [x] Persist Stripe customer/subscription IDs into `billing_settings`
- [x] Add backend tests for checkout session + webhook updates
- [x] Add frontend billing action to launch Stripe Checkout
- [x] Configure Render env vars — follow [`docs/STRIPE_RENDER_SETUP.md`](./docs/STRIPE_RENDER_SETUP.md); verify with `python scripts/verify_stripe_config.py`
- [x] Stripe webhook URL configured (`https://dbops-api.onrender.com/billing/webhook`)
- [x] Confirm Stripe webhook **event subscriptions** in dashboard — listed in `docs/STRIPE_RENDER_SETUP.md` + `GET /health/billing`

### OPS: Render + Stripe final wiring
**Labels:** `devops` `backend` `high-priority`

- [x] Set `STRIPE_SECRET_KEY` on **dbops-api** in Render
- [x] Set `STRIPE_WEBHOOK_SECRET` on **dbops-api** in Render
- [x] Set `STRIPE_PRICE_ID_STARTER` on **dbops-api** in Render
- [x] Create Stripe webhook endpoint pointing at `/billing/webhook`
- [x] Subscribe required webhook events in Stripe
- [x] Checkout flow updates billing (`billing_status=active`, Stripe IDs in `/admin/overview`)

---

## Shipped (move to Done on Trello)

### Release validation — May 10, 2026
- Live API health, auth, incidents, reports, schedules — production smoke passed

### DEVOPS: CI quality gates
- [x] Backend ruff + pytest in GitHub Actions
- [x] Frontend lint, test, build
- [x] Migration sanity (Postgres service in CI)

### TEST: Frontend App smoke suite
- [x] 16 Vitest smoke tests (`npm run test:run`)
- [x] IncidentsSection bulk-selection render loop fixed
- [x] App.jsx encoding cleanup (BOM / mojibake)

### TEST: Backend auth / RBAC integration tests
- [x] Bootstrap, login, user admin, disabled user, role matrix, rate limits, audit, billing, schedules — `backend/tests/test_auth_rbac.py`

### FEATURE: Seed demo data CLI
- [x] `python -m app seed-demo` / `python -m app` — idempotent seed; README + `test_seed_demo.py`

### FEATURE: Incident edit API + UI
- [x] `PATCH /incidents/{id}`, edit UI, history, RBAC tests

### FEATURE: Incident filters / search / sort
- [x] Query params + `IncidentsSection` filters, presets, sort, overdue

### HARDENING: Auth / session UX
- [x] 401 handling, token clear on expiry, disabled-account messages — covered in `App.test.jsx` + `App.jsx`

### FEATURE: User admin audit trail
- [x] `user_admin_audit_logs`, DBA UI table, `test_dba_user_admin_actions_are_audited`

### FEATURE: Report CSV export
- [x] `POST /reports/export/csv`, UI export button, CSV tests

### FEATURE: SSO/OIDC integration (Google PKCE)
- [x] `oidc_verify.py` — OIDC discovery, JWKS caching, RS256 ID token verification, PKCE code exchange
- [x] `OidcCallbackRequest` schema
- [x] `GET /auth/oidc/config` — public frontend config
- [x] `POST /auth/oidc/callback` — code exchange + user auto-provisioning
- [x] `GET /health/oidc` — env presence check
- [x] Frontend PKCE flow + "Sign in with SSO" button in `LoginPanel`
- [x] `render.yaml` + `.env.example` updated with `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_DEFAULT_ROLE`
- [x] End-to-end tested with Google OAuth 2.0 (Web application client)

### DOCS: Deployment guide + runbooks
- [x] `DEPLOYMENT.md` — Render deploy, env matrix, links to runbooks
- [x] [`docs/STRIPE_RENDER_SETUP.md`](./docs/STRIPE_RENDER_SETUP.md) — Render env + Stripe webhook events
- [x] [`docs/MIGRATION_ROLLBACK.md`](./docs/MIGRATION_ROLLBACK.md)
- [x] [`docs/INCIDENT_RESPONSE.md`](./docs/INCIDENT_RESPONSE.md)
- [x] `GET /health/billing` — non-secret Stripe config check

---

## Backlog

| Title | Labels |
|-------|--------|
| ROADMAP: Post-sprint enhancements | — |
| FEATURE: Scheduled report runs + notifications (enhancements) | `backend` `frontend` |
| ~~FEATURE: SSO/OIDC integration spike~~ | `backend` `security` |
| FEATURE: Trend charts + SLA widgets | `frontend` |

---

## Label reference

| Label | Scope |
|-------|-------|
| `backend` | FastAPI / Python / Alembic |
| `frontend` | React / Vite |
| `db` | Schema, migrations, seed data |
| `devops` | Docker, CI/CD, Render |
| `security` | Auth, RBAC, token handling |
| `test` | Unit / integration tests |
| `docs` | README, runbooks |
| `high-priority` | Must ship this sprint |
