# Live demo URL — Railway (production)

**Status: deployed and reachable** (verified June 2026).

| Service | URL |
|---------|-----|
| **App (buyers click this)** | https://dbops-api-production-5047.up.railway.app |
| **API + SPA** | Same URL — `Dockerfile` bundles React into the FastAPI container |
| **Health** | https://dbops-api-production-5047.up.railway.app/health → `status: ok`, PostgreSQL reachable |
| **Stripe webhook** | https://dbops-api-production-5047.up.railway.app/billing/webhook |

Use this URL in marketplace listings today. Optional: custom domain in Railway → **Settings** → **Networking**.

**CI/CD (selling point):** Push to `main` → [GitHub Actions CI](https://github.com/dallas8000-ops/DBOps-Control-Center/actions) runs (85+ backend + 21 frontend tests, lint, migrations) and Railway **auto-deploys** from `Dockerfile` + `railway.toml`. Pipeline live and verified on this production URL.

---

## Refresh deploy (after code changes)

When you push to `main`, Railway auto-deploys; no manual step required for typical code changes. If you changed `VITE_API_URL` or other build-time variables, trigger a **Redeploy** in Railway (Vite bakes env at Docker build time).

---

## One-time setup (≈30–45 minutes)

### 1. Push latest `main`

Ensure GitHub `main` is current (CI green). Railway deploys from the connected repo.

### 2. Create Railway project

1. [Railway Dashboard](https://railway.app) → **New Project** → **Deploy from GitHub** → `dallas8000-ops/DBOps-Control-Center`.
2. Railway uses `railway.toml` + root `Dockerfile` (API + frontend SPA in one service).
3. Add **PostgreSQL** (Railway plugin or Neon) and link `DATABASE_URL`.

### 3. Configure environment variables

| Variable | Value |
|----------|--------|
| `FRONTEND_ORIGINS` | `https://dbops-api-production-5047.up.railway.app` (your live URL) |
| `JWT_SECRET_KEY` | Long random secret |
| `DATABASE_URL` | PostgreSQL connection string (`?sslmode=require` if required) |
| `VITE_API_URL` | Same as your public Railway URL (build-time; set before deploy) |

**Optional for listing demo:** Stripe/OIDC can be left unset — core product works without them. Verify:

- `GET /health` → `{"status":"ok","database":"reachable",...}`
- `GET /health/billing` → shows configured flags

See [`docs/STRIPE_RAILWAY_SETUP.md`](../STRIPE_RAILWAY_SETUP.md) for live Stripe wiring.

### 4. Seed evaluation data

Railway shell or one-off command on the service:

```bash
python -m app seed-demo
```

Default users after `python -m app seed-demo` (default `SEED_PASSWORD_SALT=dbops-local-seed`):

| Role | Email | Password |
|------|-------|----------|
| DBA | `barney@example.com` | `dba-b91b26064ea0a8!` |
| Analyst | `analyst@example.com` | `analyst-6550bc46675e96!` |
| Viewer | `viewer@example.com` | `viewer-77e8e75cf1c20e!` |

Override via `SEED_DBA_PASSWORD`, `SEED_ANALYST_PASSWORD`, `SEED_VIEWER_PASSWORD` on Railway if needed.

### 5. Smoke-test the public demo

- [ ] App loads login; API health strip green  
- [ ] Analyst login → create incident → run report → export CSV  
- [ ] DBA login → user list / schedule panel visible  
- [ ] Viewer login → no create incident, no bulk checkboxes  

### 6. Protect the demo (recommended)

- Use **strong unique passwords**; rotate after workshops  
- Railway Hobby/Pro plans do not sleep like Render free tier — note uptime in listing  
- Optional: IP allowlist via Cloudflare in front of the app  
- Run `reset-demo` after public sessions if needed  

---

## Listing copy (paste-ready)

> **Live demo:** [https://dbops-api-production-5047.up.railway.app](https://dbops-api-production-5047.up.railway.app)  
> **Deployment:** Auto-deploys to Railway on every Git push to `main`; GitHub Actions CI/CD live and verified.  
> Evaluation login provided after inquiry (or publish read-only Viewer credentials).  
> Stack: Railway + PostgreSQL; same Dockerfile, `railway.toml`, and CI workflow included in source.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| **Blank page** (title/meta only, no UI) | JavaScript bundle did not run. Recipients must use a **real browser** (not email link preview). Confirm Docker build ran `npm run build` and `/opt/spa/index.html` exists. View page source: must show `<script … src="/assets/index-….js">`, **not** `/src/main.jsx`. Redeploy after fixing. |
| Web can’t reach API | `VITE_API_URL` wrong or service not rebuilt after env change |
| CORS errors | `FRONTEND_ORIGINS` must exactly match app origin (scheme + host) |
| 503 on `/health` | DB not ready; check `DATABASE_URL` and migrations on API boot |
| Slow first load | Check Railway plan limits; verify Postgres region matches app region |

**Docs:** [DEPLOYMENT.md](../../DEPLOYMENT.md), [STRIPE_RAILWAY_SETUP.md](../STRIPE_RAILWAY_SETUP.md), [deploy/DEPLOY.md](../../deploy/DEPLOY.md), [OPERATIONAL_READINESS.md](../OPERATIONAL_READINESS.md)
