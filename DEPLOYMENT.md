# DBOps Control Center — Railway Deployment Guide

> **Primary production host:** Railway (`Dockerfile` + `railway.toml`).  
> Optional buyer path: `render.yaml` (deprecated for seller demo — see [`docs/commercial-assets/LIVE_DEMO_RAILWAY_CHECKLIST.md`](./docs/commercial-assets/LIVE_DEMO_RAILWAY_CHECKLIST.md)).

## Pre-Deployment Checklist (15 min)

- [x] Backend tests pass locally: `cd backend && python -m pytest tests/ -q`
- [x] Frontend tests pass locally: `cd frontend && npm run test -- --run`
- [x] Docker Compose works end-to-end: `docker compose up --build`
- [x] Seed data runs without errors (tests cover this)
- [x] `railway.toml` and root `Dockerfile` are present
- [x] `.env` is NOT in git (`.gitignore` is correct)

## Deploy to Railway (5 minutes)

### 1. Push to GitHub (if not already done)
```bash
git add .
git commit -m "Ready for Railway deploy"
git push origin main
```

### 2. Connect Railway
1. Log in to [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub** → select `DBOps-Control-Center`
3. Railway detects `railway.toml` and builds from the root `Dockerfile`
4. Add PostgreSQL (Railway plugin or external Neon) and set `DATABASE_URL`
5. Configure environment variables (see below)

### 3. Set Environment Variables in Railway

| Key | Value | Notes |
|-----|-------|-------|
| `JWT_SECRET_KEY` | Long random secret | Required |
| `FRONTEND_ORIGINS` | `https://dbops-api-production-5047.up.railway.app` | Your live app URL |
| `DATABASE_URL` | `postgresql://...?sslmode=require` | From Railway Postgres or Neon |
| `VITE_API_URL` | Same as public Railway URL | Build-time; triggers rebuild when changed |
| `SCHEDULED_REPORTS_POLL_SECONDS` | `60` | Check for due schedules every 60s |
| `AUTH_RATE_LIMIT_MAX_REQUESTS` | `5` | Max login attempts |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | `300` | Per 5-minute window |
| `STRIPE_SECRET_KEY` | `sk_test_...` (or `sk_live_...`) | Required for checkout + webhook processing |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` | From Stripe webhook endpoint signing secret |
| `STRIPE_PRICE_ID_STARTER` | `price_...` (or `prod_...`) | Default starter plan price/product used by checkout |

**Stripe step-by-step:** [`docs/STRIPE_RAILWAY_SETUP.md`](./docs/STRIPE_RAILWAY_SETUP.md)  
**Verify after deploy:** `python scripts/verify_stripe_config.py` or `curl https://dbops-api-production-5047.up.railway.app/health/billing`

### Runbooks

- [Migration rollback](./docs/MIGRATION_ROLLBACK.md)
- [Incident response](./docs/INCIDENT_RESPONSE.md)
- [Trello board sync](./docs/TRELLO_MANUAL_SYNC.md) · [https://trello.com/b/s7LuzRWy/dbops-control-center](https://trello.com/b/s7LuzRWy/dbops-control-center)

### 4. Wait for Deployment (~5–10 minutes)
- Watch **Deployments** tab for build progress
- Migrations run automatically on first startup
- Once green, test the health endpoint:
  ```bash
  curl https://dbops-api-production-5047.up.railway.app/health
  # Expected: {"status":"ok","database":"reachable",...}
  ```

---

## 48-Hour Monitoring Checklist

### **Hour 0–1: Smoke Tests**
- [ ] Frontend loads without 404 errors
- [ ] Login page is responsive
- [ ] Bootstrap DBA creation works (first login)
- [ ] JWT tokens are issued and valid

### **Hour 1–6: Core Workflows**
- [ ] Create an incident as Analyst → resolves as DBA
- [ ] Run a report → CSV export works
- [ ] Create a schedule → next_run_at is set correctly
- [ ] Check backend logs for migration success: `alembic upgrade head`
- [ ] From DBA panel, click **Subscribe with Stripe** and confirm redirect to Stripe Checkout

### **Hour 1–6: Stripe Billing Validation**
- [ ] Open Stripe Dashboard → Developers → Webhooks
- [ ] Add endpoint: `https://<your-dbops-api-host>/billing/webhook`
- [ ] Select events:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
- [ ] Copy endpoint signing secret (`whsec_...`) into Railway `STRIPE_WEBHOOK_SECRET`
- [ ] Trigger a test checkout session from DBA panel and complete checkout in Stripe test mode
- [ ] Verify webhook deliveries show HTTP `200` in Stripe dashboard
- [ ] Verify `billing_settings` updates in product UI (`billing_status`, `stripe_customer_id`, `stripe_subscription_id`)
- [ ] Confirm `/admin/overview` shows updated billing status after webhook event delivery

### **Hour 6–24: Background Tasks**
- [ ] Scheduler loop is running (check logs for `process_due_report_schedules`)
- [ ] Rate limiting blocks excessive login attempts (test with curl loop)
- [ ] Audit logs capture user creation and incident changes

### **Hour 24–48: Stability**
- [ ] No spikes in memory or CPU usage (check Railway metrics)
- [ ] Report execution logs appear regularly (if schedule is configured)
- [ ] No database connection pool exhaustion errors
- [ ] Token refresh works correctly (no stale-token loops)

---

## Critical Logs to Watch (Railway Dashboard)

Go to your service → **Deployments** → **View Logs**

### Look for:
✅ **Good signs:**
- `alembic upgrade head` succeeds
- `Uvicorn running on 0.0.0.0:8000`
- No `SQLAlchemy` exceptions
- Scheduled report loops: `process_due_report_schedules`

❌ **Red flags:**
- `psycopg2.OperationalError` (database connectivity)
- `JWT_SECRET_KEY not set` (env var missing)
- `Missing required billing configuration: STRIPE_SECRET_KEY` (Stripe key missing)
- `Missing required billing configuration: STRIPE_WEBHOOK_SECRET` (webhook secret missing)
- `Missing required billing configuration: STRIPE_PRICE_ID_STARTER` (default price/product missing)
- `Invalid Stripe webhook signature` (secret mismatch or wrong endpoint)
- `FileNotFoundError: seed_data.json` (volume mount issue)
- `CORS error` (FRONTEND_ORIGINS mismatch)

---

## Post-Deployment Next Steps

### **If all green after 48 hours:**
1. ✅ Schedule is stable → proceed to customer onboarding
2. ✅ Apply optional hardening (retry logic, webhook backoff) in Week 5
3. ✅ Monitor first customer production use

### **If issues appear:**
1. Follow [Incident response checklist](./docs/INCIDENT_RESPONSE.md)
2. Check logs immediately (usually simple fixes: env vars, secrets)
3. Roll back deploy in Railway or follow [Migration rollback](./docs/MIGRATION_ROLLBACK.md) for schema issues
4. Fix locally, re-test in Docker Compose, re-deploy

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| `JWT_SECRET_KEY not found` | Add to Railway variables |
| `CORS error on frontend request` | Check `FRONTEND_ORIGINS` matches your domain |
| `Database connection timeout` | Postgres may take 30s to warm up; wait and retry |
| `Migrations fail on second deploy` | Idempotent (safe); usually just first-run issue |
| `Scheduler doesn't execute` | Check if schedule is `is_enabled=true` and `next_run_at <= now()` |
| `Frontend shows blank page` | Check browser console for API errors; verify `VITE_API_URL` env |
| `Stripe checkout failed: Stripe price lookup failed` | Confirm `STRIPE_PRICE_ID_STARTER` is a valid `price_...` (or a `prod_...` with an active/default recurring price) |
| `Stripe webhook returns 400` | Ensure Stripe endpoint URL is `/billing/webhook` and `STRIPE_WEBHOOK_SECRET` matches the endpoint secret |

---

## Support During 48-Hour Monitoring

- **Critical issue (DB down, auth broken):** Fix immediately, redeploy
- **Cosmetic/non-blocking (typo, layout):** Log for Week 5, don't block
- **Performance curiosity (scheduler slow):** Monitor but don't optimize yet (Amdahl's Law—scheduler runs every 60s, not user-facing)

---

## Go-Live Handoff (Post-48-Hour)

Once stable, your status is:
- ✅ **Week 1–4 all shipped**
- ✅ **20 backend tests + 12 frontend tests passing**
- ✅ **Commercial assets ready** (pricing, onboarding, SLA, demo scripts)
- ✅ **Production database + scheduled reports running**
- ⏭️ **Ready for customer onboarding** (use Day 0–7 checklist)

Document any issues found during monitoring in `/MONITORING_LOG.md` for the customer handoff.
