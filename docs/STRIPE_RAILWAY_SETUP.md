# Stripe + Railway setup

Production host: `https://dbops-api-production-5047.up.railway.app`  
Webhook URL: `https://dbops-api-production-5047.up.railway.app/billing/webhook`

## 1. Stripe Dashboard — API key and price

1. Open [Stripe Dashboard](https://dashboard.stripe.com) (use **Test mode** until go-live).
2. **Developers → API keys** → copy **Secret key** (`sk_test_...` or `sk_live_...`).
3. **Product catalog** → open **DBOps Starter** (the **$79/month** product — not RecruitCommand Pro).

   **Copy a Price ID (`price_...`) — recommended**

   Stripe hides this until you open the price itself:

   1. On the **DBOps Starter** product page, find the **Pricing** section ($79.00 / month).
   2. **Click the $79.00 monthly price row** (not just the product title).
   3. On the price detail page, open the **⋮** menu or **Details** panel — the **Price ID** starts with `price_`.
   4. Or: with that price page open, check the browser URL — it often contains `/prices/price_...`.

   If you still only see a **Product ID** (`prod_...`):

   - That `prod_...` is on the **product** header (DBOps Starter only).
   - You may paste **`prod_...` for DBOps Starter** into `STRIPE_PRICE_ID_STARTER` — the API resolves it to that product’s active recurring price.
   - **Never** paste RecruitCommand Pro’s `prod_...` or any RecruitCommand price — checkout will charge the wrong product.

   **Do not** paste a price or product from **RecruitCommand Pro**. If checkout showed the wrong product name, `STRIPE_PRICE_ID_STARTER` on Railway is wrong — replace it with DBOps Starter’s `price_...` (best) or DBOps Starter’s `prod_...`, then redeploy.

## 2. Railway — set environment variables

1. [Railway Dashboard](https://railway.app) → your DBOps service → **Variables**.
2. Add or update:

| Key | Value |
|-----|--------|
| `STRIPE_SECRET_KEY` | `sk_test_...` from step 1 |
| `STRIPE_PRICE_ID_STARTER` | **`price_...`** from DBOps Starter **$79/mo** (best). **`prod_...`** for DBOps Starter only if you cannot find the price ID — never RecruitCommand Pro. |
| `STRIPE_CHECKOUT_DISPLAY_NAME` | *(optional)* Name at top of Checkout — default `DBOps Control Center` |
| `STRIPE_WEBHOOK_SECRET` | *(step 3 — after creating webhook)* |
| `DATABASE_URL` | PostgreSQL connection string (`?sslmode=require` for Neon/Railway Postgres) |
| `JWT_SECRET_KEY` | Long random secret |
| `FRONTEND_ORIGINS` | `https://dbops-api-production-5047.up.railway.app` (your live URL) |

3. **Save** — Railway redeploys automatically.

The Dockerfile bakes `VITE_API_URL` at build time. Set it as a Railway build variable (or `ARG` in the Dockerfile) to your public API URL if you split web and API services.

## 3. Stripe — webhook endpoint and events

1. **Developers → Webhooks** → **Add endpoint**.
2. **Endpoint URL:** `https://dbops-api-production-5047.up.railway.app/billing/webhook`
3. **Select events to listen to** (required by the app):

   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`

4. Create the endpoint → reveal **Signing secret** (`whsec_...`).
5. Paste into Railway as `STRIPE_WEBHOOK_SECRET` → save → redeploy.

## 4. Verify (no secrets in output)

```bash
curl -s https://dbops-api-production-5047.up.railway.app/health/billing
```

Expected when configured:

```json
{
  "status": "ok",
  "billing": {
    "stripe_secret_key": true,
    "stripe_webhook_secret": true,
    "stripe_price_id_starter": true,
    "stripe_sdk_installed": true
  },
  "webhook_url_path": "/billing/webhook",
  "required_webhook_events": [ "..."]
}
```

If any flag is `false`, fix the matching Railway env var and redeploy.

### Checkout still shows an old business name (e.g. RecruitCommand Pro)

You do **not** need a **Branding** menu item in Stripe. The API sets checkout display name via `STRIPE_CHECKOUT_DISPLAY_NAME` (default: **DBOps Control Center**). Redeploy after pulling the latest code.

To change it globally in Stripe (optional): **Settings** (gear) → **Business** → **Public details** → **Business name**.

## 5. End-to-end test

1. Sign in as DBA on the live app.
2. **Business Metrics** → **Subscribe with Stripe** → complete test checkout.
3. Stripe **Webhooks** → recent deliveries → HTTP **200**.
4. App shows `billing_status=active` and Stripe customer/subscription IDs on **Business Metrics**.

Document results in [`MONITORING_LOG.md`](../MONITORING_LOG.md).
