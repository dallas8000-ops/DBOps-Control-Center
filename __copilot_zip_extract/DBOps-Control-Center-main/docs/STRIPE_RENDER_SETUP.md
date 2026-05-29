# Stripe + Render setup (Week 6)

Production API host used in monitoring: `https://dbops-api.onrender.com`  
Webhook URL: `https://dbops-api.onrender.com/billing/webhook`

## 1. Stripe Dashboard — API key and price

1. Open [Stripe Dashboard](https://dashboard.stripe.com) (use **Test mode** until go-live).
2. **Developers → API keys** → copy **Secret key** (`sk_test_...` or `sk_live_...`).
3. **Product catalog** → create or select **Starter** plan → copy a **Price ID** (`price_...`).  
   The API also accepts a **Product ID** (`prod_...`) if it has a default recurring price.

## 2. Render — set environment variables

1. [Render Dashboard](https://dashboard.render.com) → **dbops-api** → **Environment**.
2. Add or update:

| Key | Value |
|-----|--------|
| `STRIPE_SECRET_KEY` | `sk_test_...` from step 1 |
| `STRIPE_PRICE_ID_STARTER` | `price_...` from step 1 |
| `STRIPE_WEBHOOK_SECRET` | *(step 3 — after creating webhook)* |

3. **Save** and wait for **dbops-api** to redeploy.

4. **dbops-web** → set `VITE_API_URL` to `https://dbops-api.onrender.com` if not already set.

Keys are declared in [`render.yaml`](../render.yaml) with `sync: false` so Render prompts you to enter values (they are not committed to git).

## 3. Stripe — webhook endpoint and events

1. **Developers → Webhooks** → **Add endpoint**.
2. **Endpoint URL:** `https://dbops-api.onrender.com/billing/webhook`
3. **Select events to listen to** (required by the app):

   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`

4. Create the endpoint → reveal **Signing secret** (`whsec_...`).
5. Paste into Render as `STRIPE_WEBHOOK_SECRET` → save → redeploy **dbops-api**.

## 4. Verify (no secrets in output)

```bash
curl -s https://dbops-api.onrender.com/health/billing | jq
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

If any flag is `false`, fix the matching Render env var and redeploy.

## 5. End-to-end test

1. Sign in as DBA on the live frontend.
2. **Business Metrics** → **Subscribe with Stripe** → complete test checkout.
3. Stripe **Webhooks** → recent deliveries → HTTP **200**.
4. App shows `billing_status=active` and Stripe customer/subscription IDs on **Business Metrics**.

Document results in [`MONITORING_LOG.md`](../MONITORING_LOG.md).
