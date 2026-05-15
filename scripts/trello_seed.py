"""
DBOps Control Center — Trello Sprint Seeder
Usage: python scripts/trello_seed.py
Credentials are read from environment variables:
  TRELLO_API_KEY
  TRELLO_TOKEN
  TRELLO_BOARD_ID
"""

import os
import sys
import requests

API_KEY = os.environ.get("TRELLO_API_KEY")
TOKEN = os.environ.get("TRELLO_TOKEN")
BOARD_ID = os.environ.get("TRELLO_BOARD_ID")
BASE     = "https://api.trello.com/1"
AUTH     = {"key": API_KEY, "token": TOKEN}

if not API_KEY or not TOKEN or not BOARD_ID:
    print("Missing Trello credentials. Set TRELLO_API_KEY, TRELLO_TOKEN, and TRELLO_BOARD_ID.", file=sys.stderr)
    sys.exit(1)

def api(method, path, **kwargs):
    resp = requests.request(method, f"{BASE}{path}", params={**AUTH, **kwargs.pop("params", {})}, **kwargs)
    resp.raise_for_status()
    return resp.json()

# ── 1. Create Lists ────────────────────────────────────────────────────────────
print("Creating lists...")
lists = {}
for name in ["Backlog", "Week 6 - This Week", "Done"]:
    lst = api("POST", "/lists", params={"name": name, "idBoard": BOARD_ID, "pos": "bottom"})
    lists[name] = lst["id"]
    print(f"  ✓ {name}")

# ── 2. Create Labels ───────────────────────────────────────────────────────────
print("Creating labels...")
label_colors = {
    "backend":       "green",
    "frontend":      "blue",
    "db":            "orange",
    "devops":        "purple",
    "security":      "red",
    "test":          "sky",
    "docs":          "lime",
    "high-priority": "pink",
}
label_ids = {}
for name, color in label_colors.items():
    lbl = api("POST", "/labels", params={"name": name, "color": color, "idBoard": BOARD_ID})
    label_ids[name] = lbl["id"]
    print(f"  ✓ {name} ({color})")

# ── 3. Card definitions ────────────────────────────────────────────────────────
cards = [
    # -- Backlog --------------------------------------------------------------
    {
        "list": "Backlog",
        "name": "ROADMAP: Post-sprint Enhancements",
        "desc": "Umbrella card for items after the current Week 6 Stripe sprint.",
        "labels": [],
        "checklist": [
            "FEATURE: Scheduled report runs + notifications",
            "FEATURE: SSO/OIDC integration spike",
            "FEATURE: Trend charts + SLA widgets",
        ],
    },

    # -- Week 6 ---------------------------------------------------------------
    {
        "list": "Week 6 - This Week",
        "name": "FEATURE: Stripe billing integration wiring",
        "desc": "Finalize Stripe checkout and webhook lifecycle wiring for event-driven billing state updates.",
        "labels": ["backend", "db", "high-priority"],
        "checklist": [
            "Create feature branch from main: feature/stripe-billing-wiring",
            "Add backend endpoint POST /billing/checkout/session (DBA)",
            "Add backend endpoint POST /billing/webhook with Stripe signature verification",
            "Persist Stripe customer/subscription IDs into billing_settings",
            "Add backend tests for checkout session + webhook updates",
            "Add frontend billing action to launch Stripe Checkout",
            "Configure Render env vars: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID_STARTER",
            "Add Stripe webhook endpoint in dashboard and validate event delivery",
        ],
    },

    {
        "list": "Week 6 - This Week",
        "name": "OPS: Render + Stripe final wiring",
        "desc": "Finish deployment-level wiring for Stripe and verify end-to-end event delivery in production.",
        "labels": ["devops", "backend", "high-priority"],
        "checklist": [
            "Set STRIPE_SECRET_KEY on dbops-api in Render",
            "Set STRIPE_WEBHOOK_SECRET on dbops-api in Render",
            "Set STRIPE_PRICE_ID_STARTER on dbops-api in Render",
            "Create Stripe webhook endpoint: https://<api-domain>/billing/webhook",
            "Subscribe webhook events: checkout.session.completed, customer.subscription.updated, customer.subscription.deleted",
            "Run checkout flow from Business Ops panel",
            "Confirm billing_status and Stripe IDs update in admin overview",
        ],
    },

    {
        "list": "Done",
        "name": "RELEASE VALIDATION: May 10, 2026",
        "desc": "Live API build and production smoke checks completed (health, auth, incidents, reports, schedules).",
        "labels": ["backend", "devops"],
        "checklist": [],
    },
]

# ── 4. Create Cards + Checklists ───────────────────────────────────────────────
print("Creating cards...")
for card_def in cards:
    list_id = lists[card_def["list"]]
    label_id_list = [label_ids[l] for l in card_def["labels"]]

    card = api("POST", "/cards", params={
        "idList":   list_id,
        "name":     card_def["name"],
        "desc":     card_def["desc"],
        "idLabels": ",".join(label_id_list),
        "pos":      "bottom",
    })
    card_id = card["id"]
    print(f"  ✓ {card_def['name']}")

    if card_def.get("checklist"):
        cl = api("POST", "/checklists", params={"idCard": card_id, "name": "Checklist"})
        cl_id = cl["id"]
        for item in card_def["checklist"]:
            api("POST", f"/checklists/{cl_id}/checkItems", params={"name": item, "checked": "false"})

print("\n✅  Done! Open Trello — your sprint board is ready.")
