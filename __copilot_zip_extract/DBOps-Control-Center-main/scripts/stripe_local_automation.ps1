param(
    [ValidateSet("start", "verify")]
    [string]$Mode = "start",
    [int]$ApiPort = 8001,
    [string]$ApiHost = "0.0.0.0"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$rootEnv = Join-Path $repoRoot ".env"
$dbFile = Join-Path $backendDir "dbops_local.db"

function Get-EnvValueFromFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return ""
    }

    $line = Get-Content -LiteralPath $Path | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
    if (-not $line) {
        return ""
    }

    return ($line -split "=", 2)[1].Trim()
}

function Get-StripeExePath {
    $cmd = Get-Command stripe -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        return $cmd.Source
    }

    $wingetPath = "C:\Users\$env:USERNAME\AppData\Local\Microsoft\WinGet\Packages\Stripe.StripeCli_Microsoft.Winget.Source_8wekyb3d8bbwe\stripe.exe"
    if (Test-Path -LiteralPath $wingetPath) {
        return $wingetPath
    }

    throw "Stripe CLI not found. Install it first with: winget install --id Stripe.StripeCli -e"
}

function Get-WebhookSecret {
    param(
        [Parameter(Mandatory = $true)]
        [string]$StripeExe,
        [Parameter(Mandatory = $true)]
        [string]$ApiKey
    )

    $secret = & $StripeExe listen --api-key $ApiKey --print-secret
    $secret = ($secret | Out-String).Trim()
    if ($secret -notmatch "^whsec_") {
        throw "Failed to get local webhook signing secret from Stripe CLI."
    }
    return $secret
}

function Start-DetachedPowerShell {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        [Parameter(Mandatory = $true)]
        [string]$CommandText
    )

    $wrapped = "$host.UI.RawUI.WindowTitle = '$Title';`n$CommandText"
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $wrapped | Out-Null
}

if ($Mode -eq "verify") {
    $healthUrl = "http://localhost:$ApiPort/health/billing"
    try {
        $resp = Invoke-WebRequest -UseBasicParsing $healthUrl
        Write-Host $resp.Content
    }
    catch {
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            Write-Host ($reader.ReadToEnd())
            exit 1
        }
        throw
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $rootEnv)) {
    throw "Root .env file not found at: $rootEnv"
}

if (-not (Test-Path -LiteralPath $dbFile)) {
    throw "Local SQLite database not found at: $dbFile"
}

$stripeExe = Get-StripeExePath
$apiKey = Get-EnvValueFromFile -Path $rootEnv -Name "STRIPE_SECRET_KEY"
if ($apiKey -notmatch "^sk_(test|live)_") {
    throw "STRIPE_SECRET_KEY in .env is missing or invalid (expected sk_test_... or sk_live_...)."
}

$priceId = Get-EnvValueFromFile -Path $rootEnv -Name "STRIPE_PRICE_ID_STARTER"
if (-not $priceId) {
    throw "STRIPE_PRICE_ID_STARTER is missing in .env."
}

$webhookSecret = Get-WebhookSecret -StripeExe $stripeExe -ApiKey $apiKey
$dbUrlPath = $dbFile -replace "\\", "/"

$apiCommand = @"
Set-Location '$backendDir'
Get-Content '$rootEnv' | Where-Object { `$_ -match '^[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object {
    `$name, `$value = `$_ -split '=', 2
    Set-Item -Path "Env:$(`$name.Trim())" -Value `$value
}
`$env:DATABASE_URL = 'sqlite:///$dbUrlPath'
`$env:STRIPE_WEBHOOK_SECRET = '$webhookSecret'
uvicorn app.main:app --host $ApiHost --port $ApiPort --reload
"@

$listenerCommand = @"
`$stripeExe = '$stripeExe'
`$apiKey = '$apiKey'
& `$stripeExe listen --api-key `$apiKey --forward-to http://localhost:$ApiPort/billing/webhook
"@

Start-DetachedPowerShell -Title "DBOps API (SQLite + Stripe)" -CommandText $apiCommand
Start-DetachedPowerShell -Title "Stripe Listener -> localhost:$ApiPort" -CommandText $listenerCommand

Write-Host "Started local Stripe automation."
Write-Host "- API window: http://localhost:$ApiPort"
Write-Host "- Listener window: forwards to /billing/webhook"
Write-Host "- Local webhook secret loaded for this API run: $webhookSecret"
Write-Host ""
Write-Host "Next: open frontend and complete checkout once. Billing IDs should populate automatically."
