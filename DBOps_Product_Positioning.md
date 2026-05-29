# DBOps Control Center — Product Positioning

---

## One-line pitch

Give your operations team safe visibility into your database — without handing
anyone a SQL prompt.

**Positioning note:** This is a **licensable, deployable product** (source + migrations + CI + runbooks), not a portfolio sample or coursework artifact. The README and commercial package describe buyer deployment on **your** infrastructure.

---

## The problem it solves

Every growing team hits the same wall.

The database has the answers — incident counts, open tickets, report data,
operational metrics. But only one or two people know SQL, and raw database
access is too dangerous to hand out. So the team either waits on the developer
to run a query, or someone gets access they shouldn't have.

DBOps Control Center solves this with a controlled operations dashboard:
a DBA defines which queries are safe to run, the team runs them on demand
or on a schedule, and every action is logged. Nobody touches raw SQL.
Nobody waits on the developer.

---

## Who it's for

**Operations teams at 10–100 person companies** who need regular visibility
into their PostgreSQL database but can't justify a full BI platform or
the security risk of open database access.

**Development agencies and consultancies** who build internal tools for clients
and want a working, production-quality baseline instead of starting from scratch.

**Technical founders and engineering leads** who need to give non-engineers
controlled, audited access to operational data without writing a custom admin
panel from zero.

---

## What makes it different

Most internal tools either lock everything down (no visibility) or open
everything up (dangerous). DBOps Control Center takes a third path:

**Whitelisted SQL reports.** Every query is defined in code by a DBA.
Parameters are bound. Row counts are capped per role. No arbitrary SQL
ever executes from the browser. This is the right answer for teams that
need visibility without security risk — and it is genuinely rare in tools
at this price point.

**Three-tier RBAC enforced everywhere.** DBA, Analyst, and Viewer roles
are enforced at every API endpoint — not just the UI. A Viewer cannot
escalate to Analyst by calling the API directly. Role boundaries are
tested and verified, not assumed.

**Full audit trail out of the box.** Every admin action, every incident
state change with before/after diffs, every report execution with duration
and row count — all logged and queryable. SOC 2 conversations start
with "show me your audit trail." This answers that question on day one.

**Scheduled reports with email delivery.** Set a report to run daily or
weekly, deliver results to an email address, and log every execution.
No cron job to maintain. No manual query to remember.

---

## What's included

- Complete FastAPI backend with 30+ production-ready API routes
- React + Vite frontend dashboard
- PostgreSQL schema with Alembic migrations (9 migration versions)
- JWT authentication with bcrypt password hashing
- Three-tier RBAC (DBA / Analyst / Viewer) enforced at every endpoint
- Whitelisted SQL reporting engine with parameterized queries and CSV export
- Automated report scheduler (daily / weekly cadence)
- SMTP email delivery for scheduled reports
- Stripe billing integration with plan limits and webhook handling
- Incident workflow (create, edit, resolve, history with full audit trail)
- User lifecycle management (create, reset password, enable/disable, delete)
- Admin overview dashboard (metrics, activity trend, onboarding checklist)
- Docker Compose for local development
- Render deployment blueprint (render.yaml)
- GitHub Actions CI workflow
- Day 0 to Day 7 onboarding checklist
- Support SLA matrix (Essential / Standard / Premium tiers)
- Commercial source license

---

## What it is not

DBOps Control Center is an internal operations tool, not a compliance
certification product. It does not include SSO/OIDC integration out of the box
(available as a Tier 3 engagement), penetration testing, or custom compliance
certification work. Buyer deploys and operates on their own infrastructure.

---

## License tiers and pricing

**Tier 1 — Launch** — $8,000
Up to 5 users. Includes deployment, RBAC setup, incident workflow, and
up to 3 whitelisted reports. 2-hour handoff session included.

**Tier 2 — Growth** — $14,000
Up to 20 users. Adds scheduled reports, audit workflow tuning, and CI gates.
2 workflow refinement sessions included.

**Tier 3 — Scale** — $20,000
20+ users. Adds SSO/OIDC integration, advanced report package (up to 10 reports),
runbook and operational readiness package, and stakeholder enablement workshop.

**Monthly support add-ons:** $800 / $1,500 / $2,500 per month depending on tier.

Source license only (no hosted SaaS). Buyer deploys to their own infrastructure.
Updates included for 90 days from delivery.

---

## Contact

Barney R. Gilliom
dallas8000@gmail.com
github.com/dallas8000-ops

Pre-sales questions welcome. Enterprise and OEM licensing available on request.
