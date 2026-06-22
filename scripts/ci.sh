#!/usr/bin/env bash
# Run the same checks as GitHub Actions CI locally.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Backend ruff ==="
python -m pip install -q ruff pytest
ruff check backend/app backend/tests --select E9,F63,F7,F8,E4,E7,W

echo "=== Backend pytest ==="
(cd backend && python -m pytest -q)

echo "=== Readiness config ==="
python scripts/verify_automation_center_setup.py

echo "=== Specwright API scan ==="
python scripts/specwright_ci.py

echo "=== Frontend lint ==="
(cd frontend && npm ci && npm run lint)

echo "=== Frontend tests ==="
(cd frontend && npm run test:run)

echo "=== Frontend build ==="
(cd frontend && npm run build)

echo "All local CI checks passed."
