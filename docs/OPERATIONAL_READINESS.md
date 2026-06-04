# DBOps Control Center - Operational Readiness Package

## Overview

This document provides comprehensive operational guidance for deploying, monitoring, and maintaining DBOps Control Center in production environments.

---

## 1. Deployment Procedures

### 1.1 Prerequisites

- PostgreSQL 14+ (or managed equivalent like Render Postgres, AWS RDS)
- Python 3.11+ for local operations
- Docker and Docker Compose for local development
- Render account (or equivalent PaaS) for production deployment
- Domain name configured (optional but recommended)
- SSL certificate (required for production OIDC)

### 1.2 Environment Setup

**Required Environment Variables:**

```bash
# Core
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname
JWT_SECRET_KEY=<minimum-32-characters-random-string>
FRONTEND_ORIGINS=https://your-frontend.example.com

# Rate Limiting
AUTH_RATE_LIMIT_MAX_REQUESTS=20
AUTH_RATE_LIMIT_WINDOW_SECONDS=60
API_RATE_LIMIT_MAX_REQUESTS=120
API_RATE_LIMIT_WINDOW_SECONDS=60

# OIDC/SSO (Optional)
OIDC_ISSUER=https://accounts.google.com
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_DEFAULT_ROLE=Viewer

# SMTP (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com
SMTP_USE_TLS=1
SMTP_TIMEOUT_SECONDS=20

# Stripe (Optional)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_STARTER=price_...

# AI Assist (Optional)
OPENAI_API_KEY=sk-...
AI_REPORT_ROUTER_MODEL=gpt-4o-mini
AI_INCIDENT_SUMMARY_MODEL=gpt-4o-mini
```

### 1.3 Render Deployment

**Step 1: Connect Repository**
1. Create Render account at https://render.com
2. Connect GitHub repository
3. Use `render.yaml` blueprint for automated setup

**Step 2: Database Service**
1. Create PostgreSQL instance (Free tier for dev, Standard for prod)
2. Copy `DATABASE_URL` from Render dashboard
3. Test connection: `psql $DATABASE_URL`

**Step 3: API Service**
1. Create web service from `backend/Dockerfile`
2. Set environment variables (see 1.2)
3. Configure health check: `GET /health`
4. Enable auto-deploys on push to main

**Step 4: Frontend Service**
1. Create static site from `frontend/`
2. Set `VITE_API_URL` to API service URL
3. Build command: `npm install && npm run build`
4. Publish directory: `dist`

**Step 5: Verify Deployment**
```bash
# Health checks
curl https://your-api.onrender.com/health
curl https://your-api.onrender.com/health/oidc
curl https://your-api.onrender.com/health/billing

# UI access
open https://your-web.onrender.com
```

### 1.4 Docker Compose Local Deployment

```bash
# From repo root
docker compose up --build

# Access
# Frontend: http://localhost:5173
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## 2. Monitoring and Alerting

### 2.1 Key Metrics to Monitor

**Application Metrics:**
- API response time (p50, p95, p99)
- Error rate (5xx responses)
- Request rate (requests/second)
- Database connection pool utilization
- Memory usage
- CPU utilization

**Business Metrics:**
- Active user sessions
- Incident creation rate
- Report execution rate
- Failed report executions
- Scheduled report health

### 2.2 Render Monitoring

**Built-in Metrics:**
- CPU, Memory, Response Time available in Render dashboard
- Log streaming available in service logs
- Automatic alerts on service restarts

**Recommended Alert Thresholds:**
- Error rate > 1% for 5 minutes
- Response time p95 > 1s for 5 minutes
- Memory usage > 80% for 10 minutes
- Service restarts > 3 in 1 hour

### 2.3 Log Analysis

**Critical Log Patterns:**
```
# Database connection failures
"database connection failed"

# Authentication failures
"invalid credentials" (high rate)

# Rate limiting
"rate limit exceeded"

# Report execution failures
"report execution failed"

# Scheduler errors
"scheduler error"
```

**Log Retention:**
- Render: 7 days (free), 30 days (paid)
- Recommended: Export to external log service for long-term retention

### 2.4 Health Check Endpoints

```bash
# Overall health
GET /health
# Response: {"status":"ok","database":"reachable"}

# OIDC configuration check
GET /health/oidc
# Response: {"configured":true,"issuer":"..."}

# SMTP configuration check
GET /health/smtp
# Response: {"configured":true,"host":"..."}

# Billing configuration check
GET /health/billing
# Response: {"configured":true,"stripe_configured":true}

# Scheduler status
GET /health/scheduler
# Response: {"running":true,"last_tick":"..."}
```

**Recommended Monitoring Frequency:**
- Health checks: Every 1 minute
- Metrics collection: Every 30 seconds
- Log analysis: Real-time

---

## 3. Disaster Recovery

### 3.1 Backup Strategy

**Database Backups:**
- Render Postgres: Automatic daily backups (7-day retention)
- Manual backups before major changes
- Export backup: `pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql`

**Configuration Backups:**
- Environment variables: Document in secure password manager
- Render service configuration: Export via Render API
- Frontend build configuration: Version controlled in git

### 3.2 Recovery Procedures

**Database Recovery:**
```bash
# Restore from Render backup
# 1. Go to Render dashboard > Database > Backups
# 2. Select backup to restore
# 3. Click "Restore" (requires downtime)

# Restore from manual backup
psql $DATABASE_URL < backup_20240528.sql
```

**Service Recovery:**
```bash
# Restart API service
# Render: Manual restart from dashboard or deploy new commit

# Rollback to previous version
git revert <commit>
git push origin main
# Render auto-deploys previous version
```

**Data Recovery Time Objectives:**
- RPO (Recovery Point Objective): 24 hours (Render daily backups)
- RTO (Recovery Time Objective): 1 hour (database restore + service restart)

### 3.3 Migration Rollback

**Alembic Rollback:**
```bash
# Check current version
alembic current

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# Emergency: Full database reset (CAUTION - destroys data)
alembic downgrade base
```

**Rollback Triggers:**
- Migration failure in production
- Data corruption after migration
- Performance degradation
- Feature rollback required

See `docs/MIGRATION_ROLLBACK.md` for detailed procedures.

---

## 4. Performance Tuning

### 4.1 Database Optimization

**Index Recommendations:**
```sql
-- Incident queries
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_severity ON incidents(severity);
CREATE INDEX idx_incidents_owner ON incidents(owner);
CREATE INDEX idx_incidents_created_at ON incidents(created_at DESC);

-- Report execution logs
CREATE INDEX idx_report_execution_logs_report_key ON report_execution_logs(report_key);
CREATE INDEX idx_report_execution_logs_created_at ON report_execution_logs(created_at DESC);

-- Incident history
CREATE INDEX idx_incident_history_incident_id ON incident_history(incident_id);
CREATE INDEX idx_incident_history_created_at ON incident_history(created_at DESC);
```

**Query Optimization:**
- Use `EXPLAIN ANALYZE` for slow queries
- Monitor query performance via `report_execution_logs`
- Add row count limits to large result sets
- `GET /incidents` supports optional `limit` (1–500) and `offset`; omit `limit` to return all matches (large tenants should paginate). `GET /auth/users/audit` and `GET /reports/runs` cap at 500 rows with no cursor yet.

### 4.2 API Performance

**Caching Strategy:**
- Report catalog: Cache in memory (rarely changes)
- User directory: Cache per session (5-minute TTL)
- Incident summaries: Cache per user (1-minute TTL)

**Rate Limiting Tuning:**
```bash
# Default settings (adjust based on traffic)
AUTH_RATE_LIMIT_MAX_REQUESTS=20
AUTH_RATE_LIMIT_WINDOW_SECONDS=60
API_RATE_LIMIT_MAX_REQUESTS=120
API_RATE_LIMIT_WINDOW_SECONDS=60
```

**Connection Pooling:**
```python
# SQLAlchemy pool settings (in db.py)
pool_size=10
max_overflow=20
pool_timeout=30
pool_recycle=3600
```

### 4.3 Frontend Performance

**Build Optimization:**
- Code splitting enabled by default (Vite)
- Tree shaking removes unused code
- Asset minification enabled
- Lazy loading for large components

**Runtime Optimization:**
- Debounce search inputs (300ms)
- Virtual scrolling for large lists
- Pagination for incident lists
- Optimistic UI updates where appropriate

---

## 5. Security Hardening

### 5.1 Authentication Security

**JWT Configuration:**
```bash
# Use strong secret (minimum 32 characters)
JWT_SECRET_KEY=<use-secrets-manager-to-generate>

# Consider short-lived access tokens (future enhancement)
# ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Password Policy:**
- Minimum 8 characters
- Require at least one uppercase, one lowercase, one number
- Hashed with bcrypt (cost factor 12)
- Password reset tokens expire in 1 hour

### 5.2 Network Security

**CORS Configuration:**
```bash
# Restrict to known origins only
FRONTEND_ORIGINS=https://your-frontend.example.com,https://staging.example.com
```

**SSL/TLS:**
- Enforce HTTPS in production
- Use valid SSL certificates
- Configure HSTS headers
- Disable HTTP in production

**API Security:**
- Rate limiting on all endpoints
- Request ID correlation for audit trails
- Input validation on all endpoints
- SQL injection prevention (parameterized queries only)

### 5.3 Data Security

**Encryption:**
- Database: SSL connections required
- Secrets: Use environment variables, never in code
- Logs: Sanitize sensitive data (passwords, tokens)

**Access Control:**
- RBAC enforced at API level
- Role-based report filtering
- Audit trail for all admin actions
- Disabled users blocked immediately

### 5.4 OIDC Security

**Provider Configuration:**
- Use reputable OIDC provider (Google, Microsoft, Okta)
- Validate ID token signature
- Enforce PKCE for public clients
- Configure redirect URI exactly

**Token Handling:**
- Short-lived ID tokens
- Secure token storage (httpOnly cookies recommended)
- Immediate logout on token expiry
- No token storage in localStorage

### 5.5 Security Checklist

**Pre-Deployment:**
- [ ] JWT_SECRET_KEY is strong and unique
- [ ] FRONTEND_ORIGINS restricted to production domains
- [ ] DATABASE_URL uses SSL (sslmode=require)
- [ ] Rate limiting configured appropriately
- [ ] SMTP credentials use app-specific passwords
- [ ] Stripe keys are production keys (not test keys)
- [ ] OIDC redirect URI matches provider configuration
- [ ] All secrets stored in environment variables
- [ ] Git repository has no committed secrets
- [ ] Branch protection rules enabled

**Post-Deployment:**
- [ ] Health endpoints return 200 OK
- [ ] SSL certificate valid
- [ ] CORS headers correct
- [ ] Rate limiting functional
- [ ] Audit trail logging
- [ ] Database backups scheduled
- [ ] Monitoring alerts configured
- [ ] Log retention policy set

---

## 6. Incident Response

See `docs/INCIDENT_RESPONSE.md` for detailed incident response procedures.

**Quick Reference:**
- Severity 1 (Critical): < 15 min response, < 1 hour resolution
- Severity 2 (High): < 1 hour response, < 4 hour resolution
- Severity 3 (Medium): < 4 hour response, < 24 hour resolution
- Severity 4 (Low): < 24 hour response, < 1 week resolution

---

## 7. Maintenance Tasks

### 7.1 Daily

- Review error logs
- Check scheduled report health
- Verify backup completion
- Monitor resource utilization

### 7.2 Weekly

- Review user activity
- Check audit trail for anomalies
- Review failed report executions
- Update runbook if procedures changed

### 7.3 Monthly

- Review and rotate secrets (JWT, API keys)
- Database maintenance (VACUUM, ANALYZE)
- Review and update dependencies
- Performance tuning review
- Security audit

### 7.4 Quarterly

- Disaster recovery drill
- Security penetration test
- Capacity planning review
- Cost optimization review
- Documentation update

---

## 8. Troubleshooting

### 8.1 Common Issues

**Database Connection Failed:**
```bash
# Check DATABASE_URL format
# Verify database is accessible
# Test with psql
psql $DATABASE_URL
```

**Migration Failed:**
```bash
# Check current version
alembic current

# View migration history
alembic history

# Rollback if needed
alembic downgrade -1
```

**High Memory Usage:**
```bash
# Check connection pool size
# Review query result sizes
# Add pagination to large lists
# Consider increasing service memory
```

**Scheduled Reports Not Running:**
```bash
# Check scheduler health
curl https://your-api.onrender.com/health/scheduler

# Review schedule configuration
GET /reports/schedules

# Check for errors in logs
grep "scheduler" logs
```

### 8.2 Debug Mode

**Enable Debug Logging:**
```bash
# Set environment variable
LOG_LEVEL=DEBUG

# Restart service
# Review detailed logs
```

**Database Query Debugging:**
```python
# Enable SQLAlchemy logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
```

---

## 9. Support Contacts

**Technical Support:**
- Email: dallas8000@gmail.com
- GitHub: https://github.com/dallas8000-ops/DBOps-Control-Center/issues

**Emergency Contacts:**
- For production outages: Email with "URGENT" in subject
- Response time: < 4 hours for critical issues

---

## 10. Appendix

### 10.1 Useful Commands

```bash
# Database operations
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app seed-demo
docker compose exec backend python -m app reset-demo --yes

# API health checks
curl http://localhost:8000/health
curl http://localhost:8000/health/oidc
curl http://localhost:8000/health/billing

# Frontend operations
cd frontend
npm run build
npm run lint
npm run test:run
```

### 10.2 Resource Limits

**Minimum Requirements:**
- CPU: 1 core
- Memory: 512 MB
- Database: 1 GB storage
- Bandwidth: 10 GB/month

**Recommended for Production:**
- CPU: 2+ cores
- Memory: 1-2 GB
- Database: 10+ GB storage
- Bandwidth: 50+ GB/month

### 10.3 Cost Estimates (Render)

**Free Tier (Development):**
- Web service: Free
- Database: Free (90-day limit)
- Total: $0/month

**Production Tier:**
- Web service: $7-20/month (Standard)
- Database: $7-50/month (Standard)
- Total: $14-70/month

**Scale Tier:**
- Web service: $25-100/month (Standard+)
- Database: $50-200/month (Standard+)
- Total: $75-300/month
