# DBOps Control Center — 2-Week Sprint Board

---

## 🚀 Current Batch — Week 6 (Started May 10, 2026)

### Issue 10 — FEATURE: Stripe billing integration wiring
**Labels:** `backend` `frontend` `high-priority`

**Description:**
Wire billing scaffolding to Stripe checkout + webhook lifecycle so plan state can move from manual updates to event-driven updates.

**Checklist:**
- [x] Create feature branch from `main`: `feature/stripe-billing-wiring`
- [x] Add backend endpoint `POST /billing/checkout/session` (DBA)
- [x] Add backend endpoint `POST /billing/webhook` with Stripe signature verification
- [x] Persist Stripe customer/subscription IDs into `billing_settings`
- [x] Add backend tests for checkout session + webhook updates
- [ ] Add frontend billing action to launch Stripe Checkout
- [ ] Configure Render env vars (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_STARTER`)
- [ ] Add Stripe webhook endpoint in dashboard and validate event delivery

---

## ✅ Release Validation Update — May 10, 2026

- Live API build: `6ff1c18` (`Add billing and onboarding productization`)
- Migration verified in Render logs: `006_sched_delivery_targets -> 007_billing_onboarding`
- Health check: `GET /health` returns `{"status":"ok","database":"reachable"}`
- Authenticated validation: `/auth/me` and `/admin/overview` successful as DBA
- Production smoke pass (API-level): login, create/delete user, create/resolve incident, run report, create/disable schedule — all passed

---

## 📋 Backlog

| # | Title | Labels |
|---|-------|--------|
| — | ROADMAP: Post-sprint Enhancements | — |
| — | FEATURE: Scheduled report runs + notifications | `backend` `frontend` |
| — | FEATURE: SSO/OIDC integration spike | `backend` `security` |
| — | FEATURE: Trend charts + SLA widgets | `frontend` |

---

## 🏃 This Week — Week 1

---

### Issue 1 — FEATURE: Seed demo data CLI for local reset
**Labels:** `backend` `db` `high-priority`

**Description:**
Add a repeatable seed command that creates demo users, incidents, and report logs for local/dev environments.

**Checklist:**
- [ ] Add script/command (`python -m app.seed_demo` or similar)
- [ ] Seed users: DBA, Analyst, Viewer
- [ ] Seed 10–20 incidents with varied severity / status / owner
- [ ] Make seed idempotent (safe to rerun)
- [ ] Add README usage section
- [ ] Validate in Docker Compose flow

---

### Issue 2 — FEATURE: Incident edit API + UI form
**Labels:** `backend` `frontend` `high-priority`

**Description:**
Allow DBA/Analyst to edit incident title, description, severity, and owner with an audit-safe update flow.

**Checklist:**
- [ ] Add `PATCH /incidents/{id}`
- [ ] Validate editable fields
- [ ] Add edit button + modal/panel in UI
- [ ] Prevent unauthorized role edits
- [ ] Add success/error feedback in UI
- [ ] Add API + UI tests

---

### Issue 3 — FEATURE: Incident filters / search / sort
**Labels:** `frontend` `backend` `high-priority`

**Description:**
Enable searching incidents and filtering by status, severity, owner, and date range.

**Checklist:**
- [ ] Add filter controls in incidents section
- [ ] Add query-param support in backend list endpoint
- [ ] Add sort (newest / oldest / severity)
- [ ] Preserve filters in UI state
- [ ] Empty-state and clear-filters UX
- [ ] Test with seeded data

---

### Issue 4 — HARDENING: Auth / session UX polish
**Labels:** `frontend` `security`

**Description:**
Improve auth behavior and user messaging around token expiry and invalid session.

**Checklist:**
- [ ] Centralize 401 handling
- [ ] Force-clear token + redirect to login on expiry
- [ ] Improve auth error messages
- [ ] Add disabled-account message handling
- [ ] Verify localStorage token lifecycle

---

### Issue 5 — TEST: Backend auth / RBAC integration tests
**Labels:** `backend` `test` `high-priority`

**Description:**
Protect core routes with automated tests for the role matrix and auth flow.

**Checklist:**
- [ ] Test bootstrap registration
- [ ] Test login success / failure
- [ ] Test user-management endpoints (DBA only)
- [ ] Test disabled-user blocked behavior
- [ ] Test incident / report permissions by role
- [ ] Add test-run instructions to README

---

## 📅 Week 2 (move into "This Week" at start of week)

---

### Issue 6 — FEATURE: User admin audit trail
**Labels:** `backend` `db` `frontend`

**Description:**
Track user lifecycle actions (created, disabled, enabled, reset password, deleted) with actor and timestamp.

**Checklist:**
- [ ] Add audit table + migration
- [ ] Log admin actions server-side
- [ ] Add DBA UI table for user-action history
- [ ] Add filtering by action / email / date
- [ ] Verify audit integrity on all user actions

---

### Issue 7 — FEATURE: Report CSV export
**Labels:** `backend` `frontend`

**Description:**
Allow exporting current report results to CSV safely.

**Checklist:**
- [ ] Add backend CSV response endpoint or frontend export util
- [ ] Include headers and escaped values
- [ ] Handle large-dataset limits
- [ ] Add export button in report results block
- [ ] Add tests for CSV format

---

### Issue 8 — DEVOPS: CI quality gates
**Labels:** `devops` `test` `high-priority`

**Description:**
Enforce lint / test / build checks in CI for backend and frontend.

**Checklist:**
- [ ] Backend lint + tests
- [ ] Frontend build + lint
- [ ] Migration sanity check in CI
- [ ] Fail pipeline on critical checks
- [ ] Update README badges / CI docs

---

### Issue 9 — DOCS: Production runbook + troubleshooting
**Labels:** `docs` `devops`

**Description:**
Create a practical runbook for local, Docker, and Render operations.

**Checklist:**
- [ ] Add local startup + reset flow
- [ ] Add Docker troubleshooting section
- [ ] Add Render env-var matrix
- [ ] Add migration rollback notes
- [ ] Add incident response checklist

---

## 🏷️ Label Reference

| Label | Scope |
|-------|-------|
| `backend` | FastAPI / Python / Alembic |
| `frontend` | React / Vite |
| `db` | Schema, migrations, seed data |
| `devops` | Docker, CI/CD, Render |
| `security` | Auth, RBAC, token handling |
| `test` | Unit / integration / e2e tests |
| `docs` | README, runbooks, ADRs |
| `high-priority` | Must ship this sprint |
