# Alembic migration rollback

Migrations live in `backend/alembic/versions/`. Production runs `alembic upgrade head` on API startup.

**Current head:** `009_incident_due_at` (verify with `alembic current` in `backend/`).

## Before any rollback

1. **Backup PostgreSQL** (Render: database → **Backups** or manual `pg_dump`).
2. Note current revision:  
   `cd backend && alembic current`
3. Prefer **forward fix** (new migration) over downgrade when data has been written under the new schema.

## Downgrade one revision (local or maintenance shell)

```bash
cd backend
export DATABASE_URL="postgresql+psycopg2://..."   # same as production
alembic downgrade -1
alembic current
```

## Downgrade to a named revision

```bash
cd backend
alembic history --verbose   # list revision ids
alembic downgrade 008_incident_history
```

## Render production

1. Put the service in maintenance or stop traffic if the downgrade is destructive.
2. Open **Shell** on **dbops-api** (or run locally against production `DATABASE_URL` with extreme care):

   ```bash
   cd /app   # or your container WORKDIR
   alembic downgrade -1
   ```

3. **Redeploy the previous Git commit** that matches the older schema (downgrade code without matching migration files will fail).

4. Confirm: `curl https://dbops-api.onrender.com/health`

## Revision reference

| Revision | File | Summary |
|----------|------|---------|
| `001` | `001_initial_schema.py` | Core tables |
| `002` | `002_report_execution_logs.py` | Report audit log |
| `003` | `003_users_is_active.py` | User active flag |
| `004` | `004_user_admin_audit_logs.py` | User admin audit |
| `005` | `005_report_schedules.py` | Scheduled reports |
| `006` | `006_report_schedule_delivery_targets.py` | Delivery targets |
| `007` | `007_billing_and_onboarding.py` | Billing + onboarding |
| `008` | `008_incident_history.py` | Incident history |
| `009` | `009_incident_due_at.py` | Incident `due_at` |

## When rollback is unsafe

- After **`007_billing_and_onboarding`**: downgrading may drop billing/onboarding rows.
- After **`008` / `009`**: downgrading may drop history or `due_at` columns.

For production incidents, restore from **backup** rather than chaining multiple downgrades unless you have tested the path in staging.
