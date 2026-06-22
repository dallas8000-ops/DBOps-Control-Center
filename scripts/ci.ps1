# Run the same checks as GitHub Actions CI locally (Windows).
# Usage: powershell -File scripts/ci.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Step($name, [scriptblock]$action) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    & $action
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "$name failed (exit $LASTEXITCODE)" }
}

Step "Backend ruff" {
    python -m pip install -q ruff pytest
    ruff check backend/app backend/tests --select E9,F63,F7,F8,E4,E7,W
}

Step "Backend pytest" {
    Set-Location "$Root\backend"
    python -m pytest -q
    Set-Location $Root
}

Step "Readiness config" {
    python scripts/verify_automation_center_setup.py
}

Step "Frontend lint" {
    Set-Location "$Root\frontend"
    if (-not (Test-Path node_modules)) { npm ci }
    npm run lint
    Set-Location $Root
}

Step "Frontend tests" {
    Set-Location "$Root\frontend"
    npm run test:run
    Set-Location $Root
}

Step "Frontend build" {
    Set-Location "$Root\frontend"
    npm run build
    Set-Location $Root
}

Write-Host "`nAll local CI checks passed." -ForegroundColor Green
