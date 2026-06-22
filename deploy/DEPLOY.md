# Deployment Guide

Platform: **railway**
Framework: **react**
Production URL: https://dbops-api-production-5047.up.railway.app

## Pre-deploy checklist
1. Run readiness — aim for 80+ score
2. Switch to **live** Stripe keys in vault
3. Set DATABASE_URL and apply schema
4. Set production URL in project settings

## Environment variables
```
NODE_ENV=production
APP_URL=https://dbops-api-production-5047.up.railway.app
STRIPE_SECRET_KEY=sk_live_
STRIPE_PUBLISHABLE_KEY=pk_live_
STRIPE_WEBHOOK_SECRET=whsec_
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

## Deploy
```bash
railway up
```

## Post-deploy
1. Verify SSL: https://dbops-api-production-5047.up.railway.app
2. Test health: https://dbops-api-production-5047.up.railway.app/health
3. Verify tiers: `python scripts/verify_automation_center_setup.py`
4. Re-scan in [Deployment-Stripe-center](https://stripe-installer.gilliomfrontlinedigital.com) (target score 80+)
5. Register production Stripe webhook
6. Schedule backups: scripts/backup-db.sh
