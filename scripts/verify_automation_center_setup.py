#!/usr/bin/env python3
"""Verify DBOps is configured for Deployment-Stripe-center readiness and tier enhancements."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API_URL = os.environ.get("DBOPS_API_URL", "").strip()


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _fetch(path: str, base: str) -> tuple[int | None, dict]:
    url = f"{base.rstrip('/')}{path}"
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=25) as resp:
            return resp.status, json.loads(resp.read().decode())
    except HTTPError as exc:
        body = exc.read().decode() if exc.fp else "{}"
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"raw": body}
    except (URLError, TimeoutError) as exc:
        return None, {"error": str(exc)}


def _check_repo_files() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    required = [
        ("stripe.config.json", ROOT / "stripe.config.json"),
        ("deploy.config.json", ROOT / "deploy.config.json"),
        (".stripe-installer/stripe-manifest.json", ROOT / ".stripe-installer" / "stripe-manifest.json"),
        (".stripe-installer/portfolio-entry.json", ROOT / ".stripe-installer" / "portfolio-entry.json"),
        ("railway.toml", ROOT / "railway.toml"),
        ("scripts/backup-db.sh", ROOT / "scripts" / "backup-db.sh"),
        ("db/schema.sql", ROOT / "db" / "schema.sql"),
    ]
    for label, path in required:
        checks.append((label, path.is_file(), "present" if path.is_file() else "missing"))
    deploy = _load_json(ROOT / "deploy.config.json") or {}
    stripe = _load_json(ROOT / "stripe.config.json") or {}
    tiers_ok = len(stripe.get("tiers", [])) >= 3
    checks.append(("stripe.config tiers (3+)", tiers_ok, f"{len(stripe.get('tiers', []))} tiers"))
    checks.append(
        (
            "deploy.config healthCheckPath",
            deploy.get("healthCheckPath") == "/health",
            str(deploy.get("healthCheckPath")),
        )
    )
    return checks


def main() -> int:
    deploy = _load_json(ROOT / "deploy.config.json") or {}
    base = API_URL or deploy.get("productionUrl", "")
    print("DBOps <-> Deployment-Stripe-center verification\n")
    print(f"Repo: {ROOT}")
    print(f"API:  {base or '(set DBOPS_API_URL or productionUrl in deploy.config.json)'}\n")

    file_checks = _check_repo_files()
    file_pass = sum(1 for _, ok, _ in file_checks if ok)
    print("--- Repo config (automation center) ---")
    for label, ok, detail in file_checks:
        mark = "OK" if ok else "FAIL"
        print(f"  [{mark}] {label}: {detail}")

    if not base:
        print("\nSkipping live checks (no API URL).")
        return 0 if file_pass == len(file_checks) else 1

    live_checks: list[tuple[str, bool, str]] = []
    for path, name in [
        ("/health", "health"),
        ("/health/billing", "billing tiers"),
        ("/health/observability", "observability"),
        ("/health/scheduler", "scheduler"),
    ]:
        status, body = _fetch(path, base)
        ok = status == 200 and body.get("status") in ("ok", None)
        if path == "/health":
            ok = status == 200 and body.get("database") == "reachable"
        detail = f"HTTP {status}" if status else str(body.get("error", "unreachable"))
        if path == "/health/billing" and status == 200:
            detail += f" tier_readiness={body.get('tier_readiness', '?')}"
        live_checks.append((name, ok, detail))

    print("\n--- Live production ---")
    for name, ok, detail in live_checks:
        mark = "OK" if ok else "WARN"
        print(f"  [{mark}] {name}: {detail}")

    _, billing = _fetch("/health/billing", base)
    tier = billing.get("tier_readiness", "none")
    tier_env = billing.get("tier_env", {})
    print("\n--- Tier enhancement status ---")
    print(f"  tier_readiness: {tier}")
    for plan, configured in tier_env.items():
        print(f"  {plan}: {'configured' if configured else 'missing STRIPE_PRICE_ID_* in Railway vault'}")

    if tier == "starter":
        print("  -> Set STRIPE_PRICE_ID_PRO (+ ENTERPRISE) in Deployment-Stripe-center vault for Growth/Scale tiers.")
    elif tier == "growth":
        print("  -> Set STRIPE_PRICE_ID_ENTERPRISE for full Scale tier checkout/downgrade paths.")

    score = round((file_pass / len(file_checks)) * 50 + (sum(1 for _, ok, _ in live_checks if ok) / max(len(live_checks), 1)) * 50)
    print(f"\nEstimated readiness score: {score}/100 (re-run full scan in Deployment-Stripe-center for official score)")
    print("Installer: https://stripe-installer.gilliomfrontlinedigital.com")
    return 0 if score >= 80 else 1


if __name__ == "__main__":
    sys.exit(main())
