# The remaining ~5% — specific gaps (for buyers)

DBOps Control Center is approximately **95%** ready for a **buyer-operated production deployment**. The product is usable and shipped today; what follows is **exactly what is not finished**, so you can plan effort or support accordingly.

No vague “polish” items — five named gaps:

---

## 1. Full observability stack (metrics & tracing)

**Today:** Structured access logging, `X-Request-ID` correlation, health endpoints (`/health`, `/health/scheduler`, `/health/billing`, `/health/oidc`, `/health/smtp`).

**Not included:** Prometheus/Grafana dashboards, OpenTelemetry traces, centralized log aggregation, or alerting rules wired to schedule failures / API latency.

**Buyer impact:** You can operate with logs and health checks; you add your observability platform if you require SOC-style monitoring out of the box.

---

## 2. Incident attachments and formal escalation workflow

**Today:** Incidents with filters, `due_at`, overdue filter, edit/resolve, history with field diffs, **comments**, and **bulk actions** (acknowledge, assign, escalate severity, resolve).

**Not included:** File attachments on incidents; formal escalation states (e.g. L1 → L2 → exec); SLA policy engine beyond due-date + overdue filtering.

**Buyer impact:** Handoff notes and audit trail are covered; evidence files and enterprise ITSM-style state machines are custom work or a future phase.

---

## 3. Scheduler scale-out beyond in-process + Postgres lock

**Today:** Scheduler runs in the API process (polling loop); **PostgreSQL advisory lock** ensures one replica runs due schedules per tick; webhook/email delivery with failure stored on schedule + report execution log.

**Not included:** Dedicated worker service, Redis/queue-based lease, or multi-region active-active schedule coordination.

**Buyer impact:** Sufficient for typical single-region deployments and modest API replica count; high-scale or strict job isolation may need an external worker pattern.

---

## 4. Distributed rate limiting and token refresh

**Today:** Per-IP rate limits on auth and high-cost routes (in-memory per API instance); JWT access tokens; refresh-token migration exists (`010_refresh_tokens`) but **no** full refresh-token HTTP flow documented as production-complete.

**Not included:** Redis (or similar) shared rate-limit store across many replicas; short-lived access + documented refresh endpoint as a finished auth product.

**Buyer impact:** Works on single instance or low replica count; scale-out teams should plan Redis-backed limits and token lifecycle as a hardening sprint.

---

## 5. Deep automated test coverage on edge paths

**Today:** **69** backend pytest tests, **21** frontend Vitest smoke tests, CI on every push (ruff, pytest, lint, test, build, Alembic on Postgres).

**Not included:** Playwright/Cypress full-browser E2E; exhaustive matrices for Stripe webhook failures, SMTP outage behavior, and every schedule delivery edge case.

**Buyer impact:** Core RBAC, incidents, reports, and admin paths are gated in CI; production billing/SMTP hardening should add tests if those paths are business-critical on day one.

---

## Summary table

| # | Gap | Severity for most buyers |
|---|-----|---------------------------|
| 1 | Metrics / tracing / alerting | Medium — add your stack |
| 2 | Attachments + escalation states | Low–medium — depends on ITSM needs |
| 3 | External scheduler worker | Low until high scale |
| 4 | Distributed rate limits + token refresh | Medium at high replica count |
| 5 | E2E + billing/SMTP edge tests | Low–medium — CI covers core paths |

**Everything else described in the README “Implemented and working” section is in the box today**, including OIDC SSO, Stripe integration hooks, AI assist (heuristic + optional OpenAI), and commercial documentation.

---

*Use with [ONE_PAGE_PITCH.md](./ONE_PAGE_PITCH.md) and the main [README](../../README.md).*
