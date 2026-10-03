# Production incident response checklist

Use for **dbops-api**, **dbops-web**, and **dbops-db** on Railway.

## Severity guide

| Level | Examples | Target response |
|-------|----------|-----------------|
| **SEV-1** | API down, DB unreachable, auth broken for all users | Immediate |
| **SEV-2** | Reports/schedules failing, Stripe webhooks failing | Same day |
| **SEV-3** | UI glitch, single-user issue | Next business day |

## 1. Triage (first 5 minutes)

- [ ] Confirm scope: `curl -s https://dbops.gilliomfrontlinedigital.com/health`
- [ ] Check billing config: `curl -s https://dbops.gilliomfrontlinedigital.com/health/billing`
- [ ] Open Railway → **dbops-api** → **Logs** (last 15 min)
- [ ] Open Railway → **Metrics** (CPU, memory, 5xx)
- [ ] Note start time and symptoms in `MONITORING_LOG.md`

## 2. Common failures

| Symptom | Check | Action |
|---------|--------|--------|
| `database: unreachable` | Railway Postgres status, `DATABASE_URL` | Restart DB; verify connection string |
| `503` on checkout / webhook | `/health/billing` flags `false` | Set `STRIPE_*` env vars per [STRIPE_RAILWAY_SETUP.md](./STRIPE_RAILWAY_SETUP.md) |
| `Invalid Stripe webhook signature` | `STRIPE_WEBHOOK_SECRET` vs Stripe endpoint secret | Re-copy `whsec_...` from Stripe → Railway Variables → redeploy |
| CORS errors in browser | `FRONTEND_ORIGINS`, `VITE_API_URL` | Match live web URL to API URL |
| `401` for all users | `JWT_SECRET_KEY` changed? | Do not rotate without plan; restore previous secret or force re-login |
| Scheduler idle | `/health/scheduler`, `SCHEDULED_REPORTS_DISABLE_LOOP` | Ensure loop enabled; check `next_run_at` on schedules |

## 3. Mitigation options

- [ ] **Redeploy** latest green build (Railway → Deployments → Redeploy).
- [ ] **Rollback deploy** to previous image (Railway → Deployments → Rollback).
- [ ] **Database**: restore backup (see [MIGRATION_ROLLBACK.md](./MIGRATION_ROLLBACK.md)) — only if schema/data corruption.
- [ ] **Disable feature**: set `SCHEDULED_REPORTS_DISABLE_LOOP=true` to stop scheduler load temporarily.

## 4. Communication

- [ ] Internal: who is impacted (all users / DBA only / billing only)
- [ ] If customer-facing: status message + ETA
- [ ] After fix: what changed (env, deploy, data restore)

## 5. Post-incident (within 48 hours)

- [ ] Root cause (one paragraph)
- [ ] Permanent fix merged or env doc updated
- [ ] Add test or monitor if gap found
- [ ] Update `MONITORING_LOG.md` or runbook if steps were wrong

## Escalation contacts

Fill in for your team:

| Role | Contact |
|------|---------|
| Primary on-call | |
| DBA / data owner | |
| Stripe account owner | |
