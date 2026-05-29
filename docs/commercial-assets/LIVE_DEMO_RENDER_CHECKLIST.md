# Live demo URL — Render (production)

**Status: deployed and reachable** (verified May 2026).

| Service | URL |
|---------|-----|
| **Web (buyers click this)** | https://dbops-web.onrender.com |
| **API** | https://dbops-api.onrender.com |
| **Health** | https://dbops-api.onrender.com/health → `status: ok`, PostgreSQL reachable |
| **Stripe webhook** | https://dbops-api.onrender.com/billing/webhook |

Use this URL in marketplace listings today. Optional: custom domain (e.g. `demo.yourdomain.com` → `dbops-web`).

**CI/CD (selling point):** Push to `main` → [GitHub Actions CI](https://github.com/dallas8000-ops/DBOps-Control-Center/actions) runs (69 backend + 21 frontend tests, lint, migrations) and Render **auto-deploys** `dbops-api` + `dbops-web`. Pipeline live and verified on this production URL.

---

## Refresh deploy (after code changes)

When you push to `main`, Render auto-deploys; no manual step required for typical code changes. Use **Manual Deploy** on **dbops-web** only when you changed `VITE_*` env vars in the Render dashboard without a new commit (Vite bakes env at build time).

---

## One-time setup (≈30–45 minutes)

### 1. Push latest `main`

Ensure GitHub `main` is current (CI green). Render deploys from the connected repo.

### 2. Create Blueprint from `render.yaml`

1. Render Dashboard → **New** → **Blueprint** → connect `dallas8000-ops/DBOps-Control-Center`.
2. Apply blueprint — creates `dbops-db`, `dbops-api`, `dbops-web`.

### 3. Configure environment variables

**dbops-api**

| Variable | Value |
|----------|--------|
| `FRONTEND_ORIGINS` | `https://dbops-web.onrender.com` (your real web URL) |
| `JWT_SECRET_KEY` | Auto-generated ✓ |
| `DATABASE_URL` | From `dbops-db` ✓ |

**Optional for listing demo (recommended minimum):** leave Stripe/OIDC unset — core product works without them. Verify:

- `GET /health` → `{"status":"ok","database":"reachable",...}`
- `GET /health/billing` → shows configured flags

**dbops-web** (set **before** build — Vite bakes env at build time)

| Variable | Value |
|----------|--------|
| `VITE_API_URL` | `https://dbops-api.onrender.com` |
| `VITE_OIDC_REDIRECT_URI` | Only if OIDC demo needed |

Trigger **manual deploy** on `dbops-web` after setting `VITE_API_URL`.

### 4. Seed evaluation data

Render shell or one-off job on **dbops-api**:

```bash
python -m app seed-demo
```

Default users after `python -m app seed-demo` (default `SEED_PASSWORD_SALT=dbops-local-seed`):

| Role | Email | Password |
|------|-------|----------|
| DBA | `barney@example.com` | `dba-b91b26064ea0a8!` |
| Analyst | `analyst@example.com` | `analyst-6550bc46675e96!` |
| Viewer | `viewer@example.com` | `viewer-77e8e75cf1c20e!` |

Override via `SEED_DBA_PASSWORD`, `SEED_ANALYST_PASSWORD`, `SEED_VIEWER_PASSWORD` on Render if needed.

### 5. Smoke-test the public demo

- [ ] Web loads login; API health strip green  
- [ ] Analyst login → create incident → run report → export CSV  
- [ ] DBA login → user list / schedule panel visible  
- [ ] Viewer login → no create incident, no bulk checkboxes  

### 6. Protect the demo (recommended)

- Use **strong unique passwords**; rotate after workshops  
- Render **free tier** spins down — note “cold start ~30s” on listing  
- Optional: IP allowlist via Cloudflare in front of web  
- Run `reset-demo` after public sessions if needed  

---

## Listing copy (paste-ready)

> **Live demo:** [https://dbops-web.onrender.com](https://dbops-web.onrender.com)  
> **Deployment:** Auto-deploys to Render on every Git push to `main`; GitHub Actions CI/CD live and verified.  
> Evaluation login provided after inquiry (or publish read-only Viewer credentials).  
> Stack: Render + PostgreSQL; same blueprint and CI workflow included in source.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Web can’t reach API | `VITE_API_URL` wrong or web not rebuilt after env change |
| CORS errors | `FRONTEND_ORIGINS` must exactly match web origin (scheme + host) |
| 503 on `/health` | DB not ready; check `dbops-db` and migrations on API boot |
| Cold start | Upgrade Render plan or accept free-tier sleep in demo video |

**Docs:** [DEPLOYMENT.md](../../DEPLOYMENT.md), [STRIPE_RENDER_SETUP.md](../STRIPE_RENDER_SETUP.md), [OPERATIONAL_READINESS.md](../OPERATIONAL_READINESS.md)
