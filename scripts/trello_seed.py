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
for name in ["Backlog", "Week 1 – This Week", "Week 2", "Done"]:
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
    # ── Backlog ──────────────────────────────────────────────────────────────
    {
        "list": "Backlog",
        "name": "ROADMAP: Post-sprint Enhancements",
        "desc": "Umbrella card for post-sprint roadmap items.",
        "labels": [],
        "checklist": [
            "FEATURE: Scheduled report runs + notifications",
            "FEATURE: SSO/OIDC integration spike",
            "FEATURE: Trend charts + SLA widgets",
        ],
    },
    # ── Week 1 ───────────────────────────────────────────────────────────────
    {
        "list": "Week 1 – This Week",
        "name": "FEATURE: Seed demo data CLI for local reset",
        "desc": "Add a repeatable seed command that creates demo users, incidents, and report logs for local/dev environments.",
        "labels": ["backend", "db", "high-priority"],
        "checklist": [
            "Add script/command (python -m app.seed_demo or similar)",
            "Seed users: DBA, Analyst, Viewer",
            "Seed 10-20 incidents with varied severity/status/owner",
            "Make seed idempotent (safe to rerun)",
            "Add README usage section",
            "Validate in Docker Compose flow",
        ],
    },
    {
        "list": "Week 1 – This Week",
        "name": "FEATURE: Incident edit API + UI form",
        "desc": "Allow DBA/Analyst to edit incident title/description/severity/owner with audit-safe update flow.",
        "labels": ["backend", "frontend", "high-priority"],
        "checklist": [
            "Add PATCH /incidents/{id}",
            "Validate editable fields",
            "Add edit button + modal/panel in UI",
            "Prevent unauthorized role edits",
            "Add success/error feedback in UI",
            "Add API + UI tests",
        ],
    },
    {
        "list": "Week 1 – This Week",
        "name": "FEATURE: Incident filters / search / sort",
        "desc": "Enable searching incidents and filtering by status, severity, owner, and date range.",
        "labels": ["frontend", "backend", "high-priority"],
        "checklist": [
            "Add filter controls in incidents section",
            "Add query-param support in backend list endpoint",
            "Add sort (newest / oldest / severity)",
            "Preserve filters in UI state",
            "Empty-state and clear-filters UX",
            "Test with seeded data",
        ],
    },
    {
        "list": "Week 1 – This Week",
        "name": "HARDENING: Auth / session UX polish",
        "desc": "Improve auth behavior and user messaging around token expiry and invalid session.",
        "labels": ["frontend", "security"],
        "checklist": [
            "Centralize 401 handling",
            "Force-clear token + redirect to login on expiry",
            "Improve auth error messages",
            "Add disabled-account message handling",
            "Verify localStorage token lifecycle",
        ],
    },
    {
        "list": "Week 1 – This Week",
        "name": "TEST: Backend auth / RBAC integration tests",
        "desc": "Protect core routes with automated tests for the role matrix and auth flow.",
        "labels": ["backend", "test", "high-priority"],
        "checklist": [
            "Test bootstrap registration",
            "Test login success / failure",
            "Test user-management endpoints (DBA only)",
            "Test disabled-user blocked behavior",
            "Test incident / report permissions by role",
            "Add test-run instructions to README",
        ],
    },
    # ── Week 2 ───────────────────────────────────────────────────────────────
    {
        "list": "Week 2",
        "name": "FEATURE: User admin audit trail",
        "desc": "Track user lifecycle actions (created, disabled, enabled, reset password, deleted) with actor and timestamp.",
        "labels": ["backend", "db", "frontend"],
        "checklist": [
            "Add audit table + migration",
            "Log admin actions server-side",
            "Add DBA UI table for user-action history",
            "Add filtering by action / email / date",
            "Verify audit integrity on all user actions",
        ],
    },
    {
        "list": "Week 2",
        "name": "FEATURE: Report CSV export",
        "desc": "Allow exporting current report results to CSV safely.",
        "labels": ["backend", "frontend"],
        "checklist": [
            "Add backend CSV response endpoint or frontend export util",
            "Include headers and escaped values",
            "Handle large-dataset limits",
            "Add export button in report results block",
            "Add tests for CSV format",
        ],
    },
    {
        "list": "Week 2",
        "name": "DEVOPS: CI quality gates",
        "desc": "Enforce lint / test / build checks in CI for backend and frontend.",
        "labels": ["devops", "test", "high-priority"],
        "checklist": [
            "Backend lint + tests",
            "Frontend build + lint",
            "Migration sanity check in CI",
            "Fail pipeline on critical checks",
            "Update README badges / CI docs",
        ],
    },
    {
        "list": "Week 2",
        "name": "DOCS: Production runbook + troubleshooting",
        "desc": "Create a practical runbook for local, Docker, and Render operations.",
        "labels": ["docs", "devops"],
        "checklist": [
            "Add local startup + reset flow",
            "Add Docker troubleshooting section",
            "Add Render env-var matrix",
            "Add migration rollback notes",
            "Add incident response checklist",
        ],
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
