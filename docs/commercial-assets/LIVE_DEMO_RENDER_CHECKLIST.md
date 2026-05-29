# Live demo URL — Render deployment checklist

A **clickable HTTPS demo** converts skeptics into buyers. This repo ships `render.yaml` for a Postgres + API + static frontend stack.

---

## Target outcome

| Service | Typical URL |
|---------|-------------|
| **Web (buyers click this)** | `https://dbops-web.onrender.com` |
| **API** | `https://dbops-api.onrender.com` |
| **Health** | `https://dbops-api.onrender.com/health` |

Use custom subdomain if you brand the listing (e.g. `demo.yourdomain.com` → web service).

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

Default users: `barney@example.com` (DBA), `analyst@example.com`, `viewer@example.com` — set passwords via bootstrap or your seed docs.

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
> Evaluation login provided after inquiry (or publish read-only Viewer credentials).  
> Stack: Render + PostgreSQL; same blueprint included in source (`render.yaml`).

Replace URL with your actual Render web service URL.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Web can’t reach API | `VITE_API_URL` wrong or web not rebuilt after env change |
| CORS errors | `FRONTEND_ORIGINS` must exactly match web origin (scheme + host) |
| 503 on `/health` | DB not ready; check `dbops-db` and migrations on API boot |
| Cold start | Upgrade Render plan or accept free-tier sleep in demo video |

**Docs:** [DEPLOYMENT.md](../../DEPLOYMENT.md), [STRIPE_RENDER_SETUP.md](../STRIPE_RENDER_SETUP.md), [OPERATIONAL_READINESS.md](../OPERATIONAL_READINESS.md)
