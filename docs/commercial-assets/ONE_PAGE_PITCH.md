# DBOps Control Center — One-Page Pitch

**One line:** Give your operations team safe visibility into PostgreSQL — without handing anyone a SQL prompt.

**Contact:** Barney R. Gilliom · dallas8000@gmail.com · github.com/dallas8000-ops

---

## The problem

Growing teams need incident counts, status reports, and operational metrics from the database — but only one or two people know SQL, and raw database access is too risky to share. Teams either wait on a developer for every query, or someone gets credentials they should not have.

## Who it is for

| Buyer | Why they buy |
|--------|----------------|
| **Ops / engineering leads (10–100 people)** | Controlled visibility without a full BI stack or open DB access |
| **Agencies & consultancies** | Production-quality baseline for client internal tools — deploy under license |
| **Technical founders** | Audited incidents + whitelisted reports without building an admin panel from zero |

## What is included (source delivery)

- **Backend:** FastAPI, 30+ API routes, JWT + bcrypt, three-tier RBAC enforced on every endpoint
- **Frontend:** React + Vite operations console (incidents, reports, AI assist, DBA admin)
- **Data:** PostgreSQL schema, Alembic migrations (through `010_refresh_tokens`), Docker Compose + **Render blueprint** (`render.yaml`)
- **Security & ops:** Auth + API rate limits, request IDs, audit trails (users, incidents, report runs)
- **Product features:** Whitelisted SQL reports + CSV export, schedules (email/webhook), OIDC SSO (PKCE), Stripe billing hooks, optional AI report routing & incident summaries
- **Quality & delivery:** GitHub Actions CI on every push (69 backend tests, 21 frontend smoke tests, lint, migration sanity) + **Render auto-deploy from `main`** — production pipeline live at https://dbops-web.onrender.com
- **Commercial pack:** License (`DBOps_LICENSE.md`), pricing sheet, onboarding checklist, SLA matrix, demo scripts

**Delivery model:** Source license. Buyer deploys on **their** infrastructure (Render, AWS, self-hosted). No hosted SaaS from seller unless separately contracted.

## What makes it different

1. **Whitelisted SQL only** — parameterized reports defined by DBA; no arbitrary SQL from the browser  
2. **RBAC at the API** — Viewer / Analyst / DBA; role escalation via direct API calls is blocked and tested  
3. **Audit by default** — incident history (incl. comments), admin actions, report execution logs  
4. **Schedules + delivery** — daily/weekly UTC, email (SMTP) or webhook, execution logging  
5. **CI/CD included and proven** — push to `main` triggers GitHub Actions (ruff, pytest, frontend lint/test/build, Alembic on Postgres); Render services auto-deploy from the connected repo. **Live production** demonstrates the full loop: https://dbops-web.onrender.com · [CI badge](https://github.com/dallas8000-ops/DBOps-Control-Center/actions/workflows/ci.yml)

## Maturity: ~95% production-ready

The product is **buyer-operated**, not a prototype. Remaining work is **known and bounded** — see [REMAINING_5_PERCENT.md](./REMAINING_5_PERCENT.md) (five specific items). That transparency is intentional: buyers trust named gaps more than vague “almost done.”

## Pricing orientation (services + source)

| Tier | Indicative | Scope |
|------|------------|--------|
| **Launch** | $8,000 | ≤5 users, deploy + RBAC + incidents + up to 3 reports |
| **Growth** | $14,000 | ≤20 users, schedules, audit tuning, CI handoff |
| **Scale** | $20,000 | 20+ users, SSO hardening, expanded reports, ops workshop |

Monthly support add-ons: $800 / $1,500 / $2,500. **Source license** variants: Internal Use, Agency (3 clients), Enterprise/OEM — see [LICENSE_SALE_MODEL.md](./LICENSE_SALE_MODEL.md).

## What it is not

Not a compliance certification product, not penetration-tested as part of sale, not a multi-tenant SaaS you run for the buyer. Buyer owns security hardening, backups, and production operations.

## Before you buy — see it work

| Asset | URL |
|--------|-----|
| **Live demo (Render)** | https://dbops-web.onrender.com |
| **API / health** | https://dbops-api.onrender.com/health |
| **Demo video (5–8 min)** | Record using [DEMO_VIDEO_5-8MIN.md](./DEMO_VIDEO_5-8MIN.md) against the live URL |
| **Deploy / refresh** | [LIVE_DEMO_RENDER_CHECKLIST.md](./LIVE_DEMO_RENDER_CHECKLIST.md) |
| **Full positioning** | [`DBOps_Product_Positioning.md`](../../DBOps_Product_Positioning.md) |

Production stack is already deployed (`dbops-db`, `dbops-api`, `dbops-web` per `render.yaml`). Redeploy **dbops-web** after frontend changes so buyers see the latest commercial UI copy.

---

*Proprietary software. Use and redistribution per `DBOps_LICENSE.md` and `LEGAL_NOTICE.md`.*
