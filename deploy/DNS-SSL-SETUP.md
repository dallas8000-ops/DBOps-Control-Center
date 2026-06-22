# Domain & SSL Setup

Production URL: https://dbops-api-production-5047.up.railway.app
Domain: dbops-api-production-5047.up.railway.app
Framework: react

## SSL
SSL/TLS is automatic on Vercel, Railway, and Fly.io custom domains.

## Stripe Webhook (production)
Update webhook URL to: `https://dbops-api-production-5047.up.railway.app/billing/webhook`

## Verification
```bash
curl https://dbops-api-production-5047.up.railway.app/health
```
Run readiness from Stripe Installer after deploy.
