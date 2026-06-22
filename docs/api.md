# API Reference
_Auto-generated from FastAPI routers._

| Method | Path | Handler | Summary |
|--------|------|---------|----------|
| **GET** | `/` | `_spa_root` |  Spa Root |
| **PUT** | `/admin/billing` | `update_billing_settings` | Update Billing Settings |
| **GET** | `/admin/export` | `admin_export` | DBA-only: export all table data as a JSON snapshot for backup purposes. |
| **GET** | `/admin/hosting-monitor` | `hosting_monitor_status` | DBA-only: MRR vs Railway hosting cost; optional email when upgrade threshold is met. |
| **GET** | `/admin/overview` | `admin_overview` | Admin Overview |
| **GET** | `/admin/render-monitor` | `render_monitor_status_legacy` | Deprecated alias for /admin/hosting-monitor. |
| **POST** | `/api/ai/find-report` | `ai_find_report` | Ai Find Report |
| **POST** | `/api/ai/summarize-incident/{incident_id}` | `ai_summarize_incident` | Ai Summarize Incident |
| **POST** | `/auth/login` | `login_json` | Login Json |
| **POST** | `/auth/logout` | `logout` | Revoke the caller's refresh token (requires access JWT + matching refresh token). |
| **GET** | `/auth/me` | `me` | Me |
| **POST** | `/auth/oidc/callback` | `oidc_callback` | Exchange a PKCE authorization code for a DBOps access token. |
| **GET** | `/auth/oidc/config` | `oidc_config_endpoint` | Public OIDC config for the frontend SSO flow. No secrets returned. |
| **POST** | `/auth/refresh` | `refresh_token_endpoint` | Exchange a valid refresh token for a new access + rotated refresh token. |
| **POST** | `/auth/register` | `register_bootstrap` | First user only (role must be DBA). Further accounts use POST /auth/users as DBA. |
| **POST** | `/auth/token` | `login_form` | Login Form |
| **GET** | `/auth/users` | `list_users` | So DBAs can confirm accounts and avoid duplicate-email surprises. |
| **POST** | `/auth/users` | `register_as_dba` | Register As Dba |
| **GET** | `/auth/users/audit` | `list_user_admin_audit` | List User Admin Audit |
| **DELETE** | `/auth/users/{user_id}` | `delete_user` | Delete User |
| **PATCH** | `/auth/users/{user_id}/password` | `reset_user_password` | Reset User Password |
| **PATCH** | `/auth/users/{user_id}/status` | `set_user_status` | Set User Status |
| **POST** | `/billing/checkout/session` | `create_billing_checkout_session` | Create Billing Checkout Session |
| **POST** | `/billing/downgrade` | `downgrade_billing_plan` | Downgrade Billing Plan |
| **POST** | `/billing/webhook` | `handle_billing_webhook` | Handle Billing Webhook |
| **GET** | `/health` | `health` | Liveness plus database connectivity (SELECT 1). Returns 503 if DB unreachable. |
| **GET** | `/health/billing` | `health_billing` | Stripe env presence only (no secret values). Use after setting Railway env vars. |
| **GET** | `/health/deployment` | `health_deployment` | Automation-center readiness: env, tier, and manifest alignment (no secrets). |
| **GET** | `/health/observability` | `health_observability` | Metrics and rate-limit backend readiness (no secret values). |
| **GET** | `/health/oidc` | `health_oidc` | OIDC env presence check. No secrets returned. Verify: GET /health/oidc |
| **GET** | `/health/scheduler` | `health_scheduler` | Health Scheduler |
| **GET** | `/health/smtp` | `health_smtp` | SMTP env presence check (no secret values). Shows whether email delivery is configured. |
| **GET** | `/incidents` | `list_incidents` | List Incidents |
| **POST** | `/incidents` | `create_incident` | Create Incident |
| **PATCH** | `/incidents/actions/bulk` | `bulk_incident_action` | Bulk Incident Action |
| **PATCH** | `/incidents/{incident_id}` | `update_incident` | Update Incident |
| **POST** | `/incidents/{incident_id}/comments` | `add_incident_comment` | Add Incident Comment |
| **GET** | `/incidents/{incident_id}/history` | `get_incident_history` | Get Incident History |
| **GET** | `/incidents/{incident_id}/history/export` | `export_incident_history_csv` | Export Incident History Csv |
| **PATCH** | `/incidents/{incident_id}/resolve` | `resolve_incident` | Resolve Incident |
| **GET** | `/metrics` | `prometheus_metrics` | Prometheus Metrics |
| **GET** | `/reports/catalog` | `report_catalog` | Report Catalog |
| **POST** | `/reports/export/csv` | `export_report_csv` | Export Report Csv |
| **POST** | `/reports/run` | `run_report` | Run Report |
| **POST** | `/reports/run/bundle` | `run_essential_dependency_bundle` | Run Essential Dependency Bundle |
| **GET** | `/reports/runs` | `list_report_runs` | List Report Runs |
| **GET** | `/reports/schedules` | `list_report_schedules` | List Report Schedules |
| **POST** | `/reports/schedules` | `create_report_schedule` | Create Report Schedule |
| **PATCH** | `/reports/schedules/{schedule_id}/status` | `update_report_schedule_status` | Update Report Schedule Status |
| **GET** | `/reports/summary` | `report_summary` | Report Summary |
| **GET** | `/{full_path:path}` | `_spa_router` |  Spa Router |
