#!/usr/bin/env python3
"""Regenerate deploy/READINESS-REPORT.md from live API + repo checks."""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.automation_config import build_deployment_readiness, discover_config_root  # noqa: E402


def _fetch_json(url: str) -> dict:
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode())


def _mark(status: str) -> str:
    return {"pass": "[✓]", "warn": "[!]", "fail": "[✗]"}.get(status, "[?]")


def main() -> int:
    deploy = json.loads((ROOT / "deploy.config.json").read_text(encoding="utf-8"))
    base = os.environ.get("DBOPS_API_URL", deploy.get("productionUrl", "")).rstrip("/")
    local = build_deployment_readiness(config_root=discover_config_root() or ROOT)

    live: dict = {}
    if base:
        try:
            live = _fetch_json(f"{base}/health/deployment")
        except OSError as exc:
            live = {"error": str(exc), "score": local["score"], "checks": local["checks"]}

    payload = live if live.get("checks") else local
    score = payload.get("score", 0)
    lines = [
        "# Production Readiness Report",
        "",
        f"Score: {score}/100",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Source: {'live /health/deployment' if live.get('checks') and base else 'local automation_config'}",
        "",
    ]

    by_category: dict[str, list] = {}
    for check in payload.get("checks", []):
        by_category.setdefault(check["category"], []).append(check)

    for category, checks in sorted(by_category.items()):
        title = category.replace("_", " ").title()
        lines.append(f"## {title}")
        for check in checks:
            lines.append(f"- {_mark(check['status'])} **{check['name']}**: {check['message']}")
            if check.get("fix"):
                lines.append(f"  - Fix: {check['fix']}")
        lines.append("")

    lines.extend(
        [
            "## Automation",
            f"- Tier readiness: **{payload.get('tier_readiness', 'unknown')}**",
            "- Re-scan: https://stripe-installer.gilliomfrontlinedigital.com",
            f"- Verify: `python scripts/verify_automation_center_setup.py`",
            "",
        ]
    )

    out = ROOT / "deploy" / "READINESS-REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out} ({score}/100)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
