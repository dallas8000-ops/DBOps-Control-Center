# Trello sync — [dbops-control-center](https://trello.com/b/s7LuzRWy/dbops-control-center)

## Automatic sync (recommended)

1. **Command Palette** → **Trello Viewer: Show Saved Credentials**
2. Copy into `DBOps Control Center/.env` (template already created, gitignored):

   ```env
   TRELLO_API_KEY=your_key
   TRELLO_TOKEN=your_token
   TRELLO_BOARD_ID=s7LuzRWy
   ```

3. Run:

   ```bash
   cd "DBOps Control Center"
   python scripts/trello_sync.py
   ```

## Manual sync (browser)

### Week 6 — This Week

**FEATURE: Stripe billing integration wiring** — check all except:
- [ ] Configure Render env vars (use `docs/STRIPE_RENDER_SETUP.md`)
- [ ] Webhook event subscriptions in Stripe (four events in setup doc)

**OPS: Render + Stripe final wiring** — check:
- [x] Webhook endpoint → `https://dbops-api.onrender.com/billing/webhook`
- [x] Checkout + billing IDs in app

Leave unchecked until Render has all three `STRIPE_*` values and Stripe events are subscribed.

### Done

Move to **Done** (create if missing):
- RELEASE VALIDATION: May 10, 2026
- DEVOPS: CI quality gates
- TEST: Frontend App smoke suite stable
- Shipped Week 1–2 cards per **Shipped** section in `SPRINT_BOARD.md`
