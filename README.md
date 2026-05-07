# DBOps Control Center

Render-first portfolio app for database operations workflows (no AWS RDS/DynamoDB required).

## What this demonstrates

- PostgreSQL schema managed with **Alembic** migrations
- **JWT** authentication and **RBAC**: `DBA`, `Analyst`, `Viewer`
- Incident workflow and operational reporting APIs
- **Whitelisted read-only SQL reports** with bound parameters, row caps, and execution auditing (`report_execution_logs`)
- Docker Compose for local development
- Optional **Render** blueprint (`render.yaml`) and GitHub Actions CI

## Tech stack

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- Frontend: React, Vite
- Auth: JWT (HS256), bcrypt password hashing

## RBAC

Reports are defined in code (`backend/app/report_catalog.py`). Arbitrary SQL from clients is not executed.

| Capability | Viewer | Analyst | DBA |
|------------|--------|---------|-----|
| `GET /incidents`, `GET /reports/summary` | Yes | Yes | Yes |
| `GET /reports/catalog`, `POST /reports/run` | Yes (catalog filtered) | Yes | Yes |
| `POST /incidents` | No | Yes | Yes |
| `PATCH /incidents/{id}/resolve` | No | No | Yes |
| `POST /auth/users` (create users) | No | No | Yes |
| `GET /reports/runs` (audit trail) | No | No | Yes |

## Local development

### Docker Compose (recommended)

From this directory:

```bash
docker compose up --build
```

- API: `http://localhost:8000` (docs at `/docs`)
- Frontend: `http://localhost:5173`

Set secrets via environment or a root `.env` file used by Compose:

- `JWT_SECRET_KEY` — long random string for signing tokens
- `FRONTEND_ORIGINS` — comma-separated allowed browser origins (values are trimmed; stray quotes/trailing slashes are stripped). For Render static sites, any `https://*.onrender.com` origin is allowed by default unless you set **`CORS_DISABLE_RENDER_REGEX=true`** on the API.

### Database migrations

Inside the backend container migrations run automatically on startup via `entrypoint.sh`.

On your machine (PostgreSQL running, `DATABASE_URL` set):

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend env

Copy `frontend/.env.example` to `frontend/.env`:

- `VITE_API_URL` — API base URL (e.g. `http://localhost:8000` locally, or your deployed API URL for production builds)

```bash
cd frontend
npm install
npm run dev
```

## First-time auth bootstrap

1. Open the UI and use **First-time setup** to create the first user (must be role **DBA**), or call `POST /auth/register` once with `"role": "DBA"`.
2. Sign in with **Login**.
3. As DBA, use **Create user** in the UI or `POST /auth/users` to add Analysts and Viewers.

## Render deployment

1. Connect the repo to Render and use **Blueprint** with `render.yaml`, or create services manually.
2. **Backend**: Docker service from `backend/Dockerfile`; set `DATABASE_URL` from Render Postgres; set `JWT_SECRET_KEY` (Render can generate); set `FRONTEND_ORIGINS` to your static site URL (and `http://localhost:5173` if needed for local testing).
3. **Frontend**: Static site with root `frontend`, build `npm install && npm run build`, publish `dist`. Set `VITE_API_URL` to the public API URL **before** build so it is baked into the bundle.

If Postgres requires SSL, append query params to `DATABASE_URL` as Render documents (often `?sslmode=require`).

## API summary

- `GET /health` — public health check
- `POST /auth/register` — bootstrap first DBA only
- `POST /auth/login` — JSON login (`email`, `password`)
- `POST /auth/token` — OAuth2 password form (Swagger)
- `GET /auth/me` — current user (Bearer token)
- `POST /auth/users` — create user (DBA only)
- `GET /incidents`, `POST /incidents`, `PATCH /incidents/{id}/resolve`
- `GET /reports/summary`
- `GET /reports/catalog` — canned reports available to the current role
- `POST /reports/run` — run a whitelisted report (`report_key`, optional `params`)
- `GET /reports/runs` — recent execution audit (DBA only)

## Next enhancements

- Query plan / index benchmarking module
- Report audit retention / export
- Stricter incident severity validation
