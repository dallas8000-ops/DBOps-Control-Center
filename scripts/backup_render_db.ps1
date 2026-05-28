# DBOps Render Database Backup Script
# Usage: .\scripts\backup_render_db.ps1
# Requires: PostgreSQL client tools (psql/pg_dump) installed on your machine.
# Download from: https://www.postgresql.org/download/windows/

param(
    [string]$DatabaseUrl = "",
    [string]$OutputDir = "backups"
)

# Prompt for DATABASE_URL if not provided
if (-not $DatabaseUrl) {
    $DatabaseUrl = Read-Host "Paste your Render Internal Database URL (postgresql://...)"
}

if (-not $DatabaseUrl -or -not $DatabaseUrl.StartsWith("postgres")) {
    Write-Host "ERROR: Invalid DATABASE_URL. Must start with postgresql://" -ForegroundColor Red
    exit 1
}

# Check pg_dump is available
if (-not (Get-Command "pg_dump" -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: pg_dump not found." -ForegroundColor Red
    Write-Host "Install PostgreSQL client tools from: https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
    Write-Host "Or add it to your PATH: C:\Program Files\PostgreSQL\16\bin" -ForegroundColor Yellow
    exit 1
}

# Create output directory if it doesn't exist
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

# Generate timestamped filename
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutputFile = Join-Path $OutputDir "dbops-backup-$Timestamp.sql"

Write-Host "Backing up database to $OutputFile ..." -ForegroundColor Cyan

# Run pg_dump
$env:PGPASSWORD = ""  # pg_dump reads password from URL directly
pg_dump --no-password --clean --if-exists --format=plain "$DatabaseUrl" -f "$OutputFile"

if ($LASTEXITCODE -eq 0) {
    $Size = (Get-Item $OutputFile).Length
    if ($Size -gt 0) {
        Write-Host "Backup complete: $OutputFile ($Size bytes)" -ForegroundColor Green
    } else {
        Write-Host "WARNING: Backup file is 0 bytes — pg_dump may have failed silently." -ForegroundColor Yellow
        Remove-Item $OutputFile
        exit 1
    }
} else {
    Write-Host "ERROR: pg_dump failed with exit code $LASTEXITCODE" -ForegroundColor Red
    if (Test-Path $OutputFile) { Remove-Item $OutputFile }
    exit 1
}

Write-Host ""
Write-Host "To restore on a new Render Postgres instance:" -ForegroundColor Cyan
Write-Host "  psql `"<new-internal-database-url>`" -f `"$OutputFile`"" -ForegroundColor White
