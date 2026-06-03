"""
Sync DBOps Control Center sprint status to Trello.

Usage (from repo root):
  set TRELLO_API_KEY=...
  set TRELLO_TOKEN=...
  set TRELLO_BOARD_ID=s7LuzRWy
  python scripts/trello_sync.py

Board: https://trello.com/b/s7LuzRWy/dbops-control-center
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = REPO_ROOT / ".env"


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_dotenv(REPO_ROOT / "backend" / ".env")
load_dotenv(ENV_FILE)

API_KEY = os.environ.get("TRELLO_API_KEY")
TOKEN = os.environ.get("TRELLO_TOKEN")
BOARD_ID = os.environ.get("TRELLO_BOARD_ID", "s7LuzRWy")
BASE = "https://api.trello.com/1"
AUTH = {"key": API_KEY, "token": TOKEN}

# Exact card titles on board -> checklist item -> checked (May 2026 board layout)
CARD_CHECKLISTS: dict[str, dict[str, bool]] = {
    "TASK: Configure Render env vars for Stripe": {
        "Set STRIPE_SECRET_KEY": True,
        "Set STRIPE_WEBHOOK_SECRET": True,
        "Set STRIPE_PRICE_ID_STARTER": True,
    },
    "TASK: Add Stripe webhook endpoint and validate delivery": {
        "Create webhook endpoint in Stripe dashboard": True,
        "Subscribe required events": True,
        "Send test event and verify status update": True,
    },
    "FEATURE: Stripe billing integration wiring": {
        "Confirm scope and acceptance criteria": True,
        "Verify backend endpoint behavior": True,
        "Verify frontend launch flow": True,
    },
    "OPS: Render + Stripe final wiring": {
        "Set Render Stripe env vars": True,
        "Redeploy API and web services": True,
        "Validate billing state updates in app": True,
    },
    "DEVOPS: CI quality gates": {
        "Backend lint + tests": True,
        "Frontend build + lint": True,
        "Migration sanity check in CI": True,
        "Fail pipeline on critical checks": True,
        "Update README badges / CI docs": True,
    },
    "DOCS: Production runbook + troubleshooting": {
        "Add local startup + reset flow": True,
        "Add Docker troubleshooting section": True,
        "Add Render env-var matrix": True,
        "Add migration rollback notes": True,
        "Add incident response checklist": True,
    },
    "FEATURE: Seed demo data CLI for local reset": {
        "Add script/command (python -m app.seed_demo or similar)": True,
        "Seed users: DBA, Analyst, Viewer": True,
        "Seed 10-20 incidents with varied severity/status/owner": True,
        "Make seed idempotent (safe to rerun)": True,
        "Add README usage section": True,
        "Validate in Docker Compose flow": True,
    },
    "FEATURE: Incident edit API + UI form": {
        "Add PATCH /incidents/{id}": True,
        "Validate editable fields": True,
        "Add edit button + modal/panel in UI": True,
        "Prevent unauthorized role edits": True,
        "Add success/error feedback in UI": True,
        "Add API + UI tests": True,
    },
    "FEATURE: Incident filters / search / sort": {
        "Add filter controls in incidents section": True,
        "Add query-param support in backend list endpoint": True,
        "Add sort (newest / oldest / severity)": True,
        "Preserve filters in UI state": True,
        "Empty-state and clear-filters UX": True,
        "Test with seeded data": True,
    },
    "HARDENING: Auth / session UX polish": {
        "Centralize 401 handling": True,
        "Force-clear token + redirect to login on expiry": True,
        "Improve auth error messages": True,
        "Add disabled-account message handling": True,
        "Verify localStorage token lifecycle": True,
    },
    "TEST: Backend auth / RBAC integration tests": {
        "Test bootstrap registration": True,
        "Test login success / failure": True,
        "Test user-management endpoints (DBA only)": True,
        "Test disabled-user blocked behavior": True,
        "Test incident / report permissions by role": True,
        "Add test-run instructions to README": True,
    },
    "FEATURE: User admin audit trail": {
        "Add audit table + migration": True,
        "Log admin actions server-side": True,
        "Add DBA UI table for user-action history": True,
        "Add filtering by action / email / date": True,
        "Verify audit integrity on all user actions": True,
    },
    "FEATURE: Report CSV export": {
        "Add backend CSV response endpoint or frontend export util": True,
        "Include headers and escaped values": True,
        "Handle large-dataset limits": True,
        "Add export button in report results block": True,
        "Add tests for CSV format": True,
    },
}

# Cards to move to Done when every checklist item above is checked (or listed here explicitly)
FORCE_DONE_CARDS = {
    "RELEASE VALIDATION: May 10, 2026",
}

# Optional: cards that shipped in repo but may not exist on the board yet
MOVE_TO_DONE_WHEN_SYNCED = [
    "TASK: Configure Render env vars for Stripe",
    "TASK: Add Stripe webhook endpoint and validate delivery",
    "FEATURE: Stripe billing integration wiring",
    "OPS: Render + Stripe final wiring",
    "DEVOPS: CI quality gates",
    "DOCS: Production runbook + troubleshooting",
    "FEATURE: Seed demo data CLI for local reset",
    "FEATURE: Incident edit API + UI form",
    "FEATURE: Incident filters / search / sort",
    "HARDENING: Auth / session UX polish",
    "TEST: Backend auth / RBAC integration tests",
    "TEST: Frontend App smoke suite stable",
    "FEATURE: User admin audit trail",
    "FEATURE: Report CSV export",
    "FEATURE: Render upgrade monitor",
    "FEATURE: Marketing landing page",
    "DOCS: Terms of Service v1.1 + downgrade billing",
    "FEATURE: Billing plan catalog + checkout metadata",
    "OPS: Growth-tier observability and E2E",
]

OPEN_SPRINT_CARDS: list[str] = []

NEW_DONE_CARDS = [
    {
        "name": "DEVOPS: CI quality gates",
        "desc": "GitHub Actions: ruff, pytest, frontend lint/test/build, migration sanity.",
        "labels": ["devops", "test"],
        "checklist": [
            "Backend lint + tests",
            "Frontend build + lint",
            "Migration sanity check in CI",
            "Fail pipeline on critical checks",
            "Update README badges / CI docs",
        ],
        "checked": [True, True, True, True, True],
    },
    {
        "name": "TEST: Frontend App smoke suite stable",
        "desc": "Fixed IncidentsSection render loop; 16 Vitest smoke tests pass; App.jsx encoding cleanup.",
        "labels": ["frontend", "test"],
        "checklist": [
            "Fix hanging vitest suite",
            "Fix IncidentsSection bulk-selection effect loop",
            "Strip UTF-8 BOM / mojibake in App.jsx",
            "Backend lint: remove unused import; models _utcnow()",
        ],
        "checked": [True, True, True, True],
    },
    {
        "name": "FEATURE: Render upgrade monitor",
        "desc": "GET /admin/render-monitor; MRR vs Render cost; SMTP alert at 3x threshold; daily scheduler check.",
        "labels": ["backend", "devops"],
        "checklist": [
            "Add render_monitor.py + DBA endpoint",
            "Wire scheduler daily check",
            "SMTP alert to ALERT_EMAIL",
            "Tests + env vars on Render",
        ],
        "checked": [True, True, True, True],
    },
    {
        "name": "FEATURE: Marketing landing page",
        "desc": "Public landing page before login: hero, features, pricing, contact, terms link.",
        "labels": ["frontend"],
        "checklist": [
            "LandingPage.jsx",
            "Wire showLanding in App.jsx",
            "Terms of service footer link",
        ],
        "checked": [True, True, True],
    },
    {
        "name": "DOCS: Terms of Service v1.1 + downgrade billing",
        "desc": "Terms v1.1; POST /billing/downgrade; pending plan on invoice.paid webhook.",
        "labels": ["docs", "backend"],
        "checklist": [
            "Update DBOps_TERMS_OF_SERVICE.md",
            "Downgrade API + webhook lifecycle",
            "Frontend downgrade button",
        ],
        "checked": [True, True, True],
    },
    {
        "name": "FEATURE: Billing plan catalog + checkout metadata",
        "desc": "PLAN_CATALOG limits; Stripe checkout session metadata; webhook auto-apply limits.",
        "labels": ["backend", "frontend"],
        "checklist": [
            "billing_plans.py catalog",
            "Checkout session plan_key metadata",
            "Webhook applies plan limits",
        ],
        "checked": [True, True, True],
    },
    {
        "name": "OPS: Growth-tier observability and E2E",
        "desc": "Prometheus /metrics, optional Redis rate limits, Playwright E2E, Grafana dashboard template.",
        "labels": ["devops", "test"],
        "checklist": [
            "GET /metrics + observability health",
            "REDIS_URL optional shared rate limits",
            "Playwright commercial E2E in CI",
            "Grafana dashboard JSON + docs",
        ],
        "checked": [True, True, True, True],
    },
]


def require_credentials() -> None:
    if not API_KEY or not TOKEN:
        print(
            "Missing Trello credentials.\n"
            "Add to DBOps Control Center/.env (gitignored):\n"
            "  TRELLO_API_KEY=...\n"
            "  TRELLO_TOKEN=...\n"
            "  TRELLO_BOARD_ID=s7LuzRWy\n"
            "Use the same key/token as Trello Viewer (Command Palette -> Trello Viewer: Show Saved Credentials).\n"
            "Get a token: https://trello.com/app-key",
            file=sys.stderr,
        )
        sys.exit(1)


def api(method: str, path: str, **kwargs: Any) -> Any:
    params = {**AUTH, **kwargs.pop("params", {})}
    resp = requests.request(method, f"{BASE}{path}", params=params, timeout=30, **kwargs)
    if not resp.ok:
        print(f"Trello API error {resp.status_code}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    if resp.text:
        return resp.json()
    return None


def resolve_board_id() -> str:
    board = api("GET", f"/boards/{BOARD_ID}", params={"fields": "id,name,shortLink"})
    print(f"Board: {board['name']} ({board.get('shortLink', BOARD_ID)})")
    return board["id"]


def load_lists(board_id: str) -> dict[str, str]:
    lists = api("GET", f"/boards/{board_id}/lists", params={"fields": "name", "filter": "open"})
    return {lst["name"]: lst["id"] for lst in lists}


def load_labels(board_id: str) -> dict[str, str]:
    labels = api("GET", f"/boards/{board_id}/labels", params={"limit": 100})
    by_name: dict[str, str] = {}
    for lbl in labels:
        name = (lbl.get("name") or "").strip()
        if name:
            by_name[name] = lbl["id"]
    return by_name


def load_cards(board_id: str) -> dict[str, dict[str, Any]]:
    cards = api(
        "GET",
        f"/boards/{board_id}/cards",
        params={"fields": "name,idList", "filter": "open"},
    )
    return {card["name"]: card for card in cards}


def sync_checklist(card_id: str, card_name: str, desired: dict[str, bool]) -> None:
    checklists = api("GET", f"/cards/{card_id}/checklists")
    if not checklists:
        print(f"  ! No checklist on card: {card_name}")
        return

    for checklist in checklists:
        for item in checklist.get("checkItems", []):
            item_name = item["name"]
            if item_name not in desired:
                continue
            checked = desired[item_name]
            state = "complete" if checked else "incomplete"
            if item.get("state") != state:
                api(
                    "PUT",
                    f"/cards/{card_id}/checkItem/{item['id']}",
                    params={"state": state},
                )
                mark = "x" if checked else " "
                print(f"  [{mark}] {item_name}")


def move_card(card_id: str, list_id: str, card_name: str, list_name: str) -> None:
    api("PUT", f"/cards/{card_id}", params={"idList": list_id})
    print(f"  -> moved to {list_name}")


def ensure_done_card(
    board_id: str,
    lists: dict[str, str],
    labels: dict[str, str],
    cards_by_name: dict[str, dict[str, Any]],
    spec: dict[str, Any],
) -> None:
    done_id = lists.get("Done")
    if not done_id:
        print("  ! 'Done' list not found — skip creating", spec["name"])
        return

    if spec["name"] in cards_by_name:
        return

    label_ids = [labels[l] for l in spec.get("labels", []) if l in labels]
    card = api(
        "POST",
        "/cards",
        params={
            "idList": done_id,
            "name": spec["name"],
            "desc": spec["desc"],
            "idLabels": ",".join(label_ids),
            "pos": "bottom",
        },
    )
    card_id = card["id"]
    print(f"  + created Done card: {spec['name']}")

    cl = api("POST", "/checklists", params={"idCard": card_id, "name": "Checklist"})
    for item_name, checked in zip(spec["checklist"], spec["checked"], strict=True):
        item = api(
            "POST",
            f"/checklists/{cl['id']}/checkItems",
            params={"name": item_name, "checked": "true" if checked else "false"},
        )
        if checked and item.get("state") != "complete":
            api(
                "PUT",
                f"/cards/{card_id}/checkItem/{item['id']}",
                params={"state": "complete"},
            )


def main() -> None:
    require_credentials()
    board_id = resolve_board_id()
    lists = load_lists(board_id)
    labels = load_labels(board_id)
    cards_by_name = load_cards(board_id)

    if not lists:
        print("No lists on board. Run scripts/trello_seed.py first.", file=sys.stderr)
        sys.exit(1)

    done_id = lists.get("Done")
    active_id = (
        lists.get("Week 6 - This Week")
        or lists.get("This Week")
        or lists.get("In Progress")
        or lists.get("Backlog")
    )

    print("\nSyncing checklists...")
    for card_name, checklist in CARD_CHECKLISTS.items():
        card = cards_by_name.get(card_name)
        if not card:
            print(f"  ! Card not found: {card_name}")
            continue
        print(f"\n{card_name}")
        sync_checklist(card["id"], card_name, checklist)

    print("\nEnsuring shipped cards exist in Done...")
    for spec in NEW_DONE_CARDS:
        ensure_done_card(board_id, lists, labels, cards_by_name, spec)

    cards_by_name = load_cards(board_id)

    print("\nMoving shipped cards to Done...")
    if done_id:
        for card_name in MOVE_TO_DONE_WHEN_SYNCED:
            card = cards_by_name.get(card_name)
            if card and card["idList"] != done_id:
                move_card(card["id"], done_id, card_name, "Done")

        for card_name in FORCE_DONE_CARDS:
            card = cards_by_name.get(card_name)
            if card and card["idList"] != done_id:
                move_card(card["id"], done_id, card_name, "Done")

    print("\nKeeping open sprint cards out of Done...")
    if active_id and done_id:
        for card_name in OPEN_SPRINT_CARDS:
            card = cards_by_name.get(card_name)
            if card and card["idList"] == done_id:
                move_card(card["id"], active_id, card_name, next(k for k, v in lists.items() if v == active_id))

    print("\nDone. Open: https://trello.com/b/s7LuzRWy/dbops-control-center")


if __name__ == "__main__":
    main()
