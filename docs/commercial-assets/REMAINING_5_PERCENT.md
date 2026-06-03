# Growth-tier readiness — 100% for $13,800 sales

DBOps Control Center is **100% ready for Growth-tier buyers** (10–100 person teams, single-region Render/AWS deploy). Enterprise-only gaps remain optional upsells.

---

## Shipped for Growth-tier (100%)

| Area | Status | Where |
|------|--------|--------|
| Core product | ✅ | RBAC, incidents, reports, schedules, OIDC, AI assist |
| Marketing + legal | ✅ | Landing page, Terms v1.1, `/terms-of-service.html` |
| Stripe billing | ✅ | Checkout, webhooks (`invoice.paid`), plan limits, downgrade at next cycle |
| Auth hardening | ✅ | Refresh token rotation (`POST /auth/refresh`, `POST /auth/logout`) |
| Rate limits | ✅ | Per-IP limits; optional **`REDIS_URL`** for multi-replica shared limits |
| Observability | ✅ | `GET /metrics` (Prometheus), `GET /health/observability`, Grafana template |
| Automated quality | ✅ | 78+ backend pytest, 21 frontend Vitest, Playwright E2E (landing + terms), CI |

See [`docs/observability/README.md`](../observability/README.md) for Prometheus/Grafana setup.

---

## Optional enterprise upsells (not required for Growth sale)

These were the original “~5%” gaps. **Do not block a $13,800 Growth deal** unless the buyer explicitly asks:

| # | Gap | When to sell it |
|---|-----|-----------------|
| 1 | Full hosted observability stack | Buyer wants SOC-style monitoring managed for them |
| 2 | Incident file attachments + ITSM escalation states | Buyer runs formal L1/L2/ exec workflows |
| 3 | External scheduler worker / Redis job queue | Buyer needs many API replicas or multi-region |
| 4 | Playwright E2E through full login + billing UI | Buyer demands browser CI for every admin flow |
| 5 | SOC 2 / pen test / compliance certification | Separate services engagement |

---

## Buyer transparency script

> “Growth delivery is production-ready today: audited SQL, RBAC, schedules, Stripe billing, refresh tokens, Prometheus metrics, and CI-gated tests. Enterprise items like attachments, external workers, or compliance audits are scoped separately if you need them.”

---

*Pair with [ONE_PAGE_PITCH.md](./ONE_PAGE_PITCH.md), [pricing-sheet.md](./pricing-sheet.md), and the main [README](../../README.md).*
