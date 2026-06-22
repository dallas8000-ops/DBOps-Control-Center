#!/usr/bin/env python3
"""Specwright-style API scan for DBOps CI (AST routes, OpenAPI drift, score gate)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Local vendored scanner (from dallas8000-ops/Specwright, MIT-compatible reuse)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from specwright_fastapi_scanner import analyze_fastapi, collect_routes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
APP_DIR = BACKEND / "app"
TESTS_DIR = BACKEND / "tests"
OPENAPI_PATH = ROOT / "docs" / "openapi.yaml"
API_MD_PATH = ROOT / "docs" / "api.md"
SCORE_PATH = ROOT / "docs" / "specwright-score.json"


def _collect_python_files() -> list[Path]:
    skip = {"__pycache__", ".venv", "venv", "alembic"}
    files: list[Path] = []
    for base in (APP_DIR,):
        if not base.is_dir():
            return files
        for path in base.rglob("*.py"):
            if any(part in skip for part in path.parts):
                continue
            files.append(path)
    return files


def _read_tests() -> str:
    if not TESTS_DIR.is_dir():
        return ""
    parts = []
    for path in TESTS_DIR.rglob("test_*.py"):
        try:
            parts.append(path.read_text(encoding="utf-8"))
        except OSError:
            pass
    return "\n".join(parts)


def _route_key(route: dict) -> str:
    return f"{route.get('method', 'GET')} {route.get('path', '/')}"


def _coverage_rows(routes: list[dict], test_content: str, openapi: str, api_md: str) -> list[dict]:
    rows = []
    for r in routes:
        path = r.get("path", "")
        name = r.get("name", "")
        has_test = any(
            p and p in test_content
            for p in (f"test_{name}", f"def test_{name}", path.replace("{", "").replace("}", ""))
            if p != "/"
        )
        has_docs = (path in openapi or (name and name in openapi)) and (
            path in api_md or (name and name in api_md)
        )
        if has_test and has_docs:
            status = "green"
        elif has_test or has_docs:
            status = "amber"
        else:
            status = "red"
        rows.append(
            {
                "method": r.get("method", "GET"),
                "path": path,
                "handler": name,
                "has_test": has_test,
                "has_docs": has_docs,
                "status": status,
            }
        )
    return rows


def _compute_score(rows: list[dict], drift: bool) -> dict:
    n = len(rows) or 1
    green = sum(1 for r in rows if r["status"] == "green")
    test_pct = sum(1 for r in rows if r["has_test"]) / n * 100
    doc_pct = sum(1 for r in rows if r["has_docs"]) / n * 100
    full_pct = green / n * 100
    freshness = 0 if drift else 100
    raw = doc_pct * 0.35 + test_pct * 0.35 + full_pct * 0.20 + freshness * 0.10
    score = int(min(100, max(0, round(raw))))
    return {
        "score": score,
        "grade": "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F",
        "breakdown": {
            "documentation_pct": round(doc_pct, 1),
            "test_coverage_pct": round(test_pct, 1),
            "fully_covered_pct": round(full_pct, 1),
            "freshness_pct": freshness,
        },
        "route_count": len(rows),
    }


def _code_mtime() -> float:
    latest = 0.0
    for path in _collect_python_files():
        try:
            latest = max(latest, path.stat().st_mtime)
        except OSError:
            pass
    return latest


def run(*, write: bool, min_score: int) -> int:
    files = _collect_python_files()
    if not files:
        print("::error::No Python files under backend/app", file=sys.stderr)
        return 1

    openapi, api_md = analyze_fastapi(files, BACKEND)
    routes = collect_routes(files, BACKEND)
    on_disk = OPENAPI_PATH.read_text(encoding="utf-8") if OPENAPI_PATH.exists() else ""
    drift = bool(on_disk.strip()) and on_disk.strip() != openapi.strip()

    if write or not OPENAPI_PATH.exists():
        OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
        OPENAPI_PATH.write_text(openapi + "\n", encoding="utf-8")
        API_MD_PATH.write_text(api_md, encoding="utf-8")
        print(f"Wrote {OPENAPI_PATH.relative_to(ROOT)} ({len(routes)} routes)")
        drift = False

    spec_mtime = OPENAPI_PATH.stat().st_mtime if OPENAPI_PATH.exists() else 0
    stale = spec_mtime < _code_mtime() - 60 and drift

    test_content = _read_tests()
    api_md_disk = API_MD_PATH.read_text(encoding="utf-8") if API_MD_PATH.exists() else api_md
    openapi_disk = OPENAPI_PATH.read_text(encoding="utf-8") if OPENAPI_PATH.exists() else openapi
    rows = _coverage_rows(routes, test_content, openapi_disk, api_md_disk)
    score_data = _compute_score(rows, drift=drift or stale)
    score_data["drift_detected"] = drift or stale
    score_data["tool"] = "specwright-ci"
    score_data["spec_path"] = str(OPENAPI_PATH.relative_to(ROOT))

    SCORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORE_PATH.write_text(json.dumps(score_data, indent=2) + "\n", encoding="utf-8")

    print(f"Specwright score: {score_data['score']}/100 ({score_data['grade']}) — {len(routes)} routes")
    print(
        f"  docs {score_data['breakdown']['documentation_pct']}% | "
        f"tests {score_data['breakdown']['test_coverage_pct']}% | "
        f"fresh {'no' if score_data['drift_detected'] else 'yes'}"
    )

    if stale and not write:
        print("::error::OpenAPI spec is stale — run: python scripts/specwright_ci.py --write", file=sys.stderr)
        return 1

    if score_data["score"] < min_score:
        print(
            f"::error::Specwright score {score_data['score']} below minimum {min_score}",
            file=sys.stderr,
        )
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Specwright CI gate for DBOps FastAPI")
    parser.add_argument("--write", action="store_true", help="Regenerate docs/openapi.yaml and api.md")
    parser.add_argument("--min-score", type=int, default=int(__import__("os").getenv("SPECWRIGHT_MIN_SCORE", "45")))
    args = parser.parse_args()
    return run(write=args.write, min_score=args.min_score)


if __name__ == "__main__":
    sys.exit(main())
