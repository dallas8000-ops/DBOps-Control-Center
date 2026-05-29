param(
    [ValidateSet("start", "stop", "status")]
    [string]$Mode = "start",
    [int]$ApiPort = 8000,
    [int]$WebPort = 5173,
    [string]$ApiHost = "0.0.0.0",
    [string]$WebHost = "0.0.0.0"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
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

function Get-PythonExe {
    $venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }

    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py -and $py.Source) {
        return $py.Source
    }

    throw "Python executable not found. Create .venv or install Python on PATH."
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

    return ""
}

function Start-BackgroundProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        [Parameter(Mandatory = $true)]
        [string]$CommandText
    )

    $scriptFile = Join-Path $env:TEMP "$Title.ps1"
    $CommandText | Out-File -FilePath $scriptFile -Encoding UTF8
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $scriptFile -WindowStyle Hidden
}

function Stop-ListenerOnPort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
        try {
            Stop-Process -Id $listener.OwningProcess -Force -ErrorAction Stop
            Write-Host ("Stopped PID {0} on port {1}" -f $listener.OwningProcess, $Port)
        }
        catch {
            Write-Host ("Could not stop PID {0} on port {1}: {2}" -f $listener.OwningProcess, $Port, $_.Exception.Message)
        }
    }
}

function Stop-StripeForwarder {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $target = "--forward-to http://localhost:$Port/billing/webhook"
    $stripeProcs = Get-CimInstance Win32_Process -Filter "Name = 'stripe.exe'" -ErrorAction SilentlyContinue
    foreach ($proc in $stripeProcs) {
        if ($proc.CommandLine -and $proc.CommandLine.Contains($target)) {
            try {
                Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
                Write-Host ("Stopped Stripe listener PID {0}" -f $proc.ProcessId)
            }
            catch {
                Write-Host ("Could not stop Stripe listener PID {0}: {1}" -f $proc.ProcessId, $_.Exception.Message)
            }
        }
    }
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

if ($Mode -eq "stop") {
    Stop-ListenerOnPort -Port $ApiPort
    Stop-ListenerOnPort -Port $WebPort
    Stop-StripeForwarder -Port $ApiPort
    Get-Job | Stop-Job | Remove-Job
    Write-Host "Local dev stack stopped."
    exit 0
}

if ($Mode -eq "status") {
    foreach ($check in @("/health", "/health/oidc", "/health/billing")) {
        try {
            $res = Invoke-WebRequest -UseBasicParsing "http://localhost:$ApiPort$check" -ErrorAction Stop
            Write-Host ("API {0} -> {1}" -f $check, [int]$res.StatusCode)
        }
        catch {
            if ($_.Exception.Response) {
                Write-Host ("API {0} -> {1}" -f $check, [int]$_.Exception.Response.StatusCode)
            }
            else {
                Write-Host ("API {0} -> unreachable" -f $check)
            }
        }
    }

    try {
        $web = Invoke-WebRequest -UseBasicParsing "http://localhost:$WebPort" -ErrorAction Stop
        Write-Host ("Web / -> {0}" -f [int]$web.StatusCode)
    }
    catch {
        Write-Host "Web / -> unreachable"
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $rootEnv)) {
    throw "Root .env file not found at: $rootEnv"
}

if (-not (Test-Path -LiteralPath $backendDir)) {
    throw "Backend directory not found at: $backendDir"
}

if (-not (Test-Path -LiteralPath $frontendDir)) {
    throw "Frontend directory not found at: $frontendDir"
}

if (-not (Test-Path -LiteralPath $dbFile)) {
    throw "Local SQLite database not found at: $dbFile"
}

$pythonExe = Get-PythonExe
$dbUrlPath = $dbFile -replace "\\", "/"

Stop-ListenerOnPort -Port $ApiPort
Stop-ListenerOnPort -Port $WebPort
Stop-StripeForwarder -Port $ApiPort

$stripeApiKey = Get-EnvValueFromFile -Path $rootEnv -Name "STRIPE_SECRET_KEY"
$stripeExe = Get-StripeExePath
$webhookSecret = ""

if ($stripeApiKey -and $stripeExe) {
    try {
        $webhookSecret = Get-WebhookSecret -StripeExe $stripeExe -ApiKey $stripeApiKey
    }
    catch {
        Write-Host ("Stripe webhook secret fetch failed: {0}" -f $_.Exception.Message)
        Write-Host "Continuing without overriding STRIPE_WEBHOOK_SECRET for this run."
    }
}

$apiCommand = @"
Set-Location '$backendDir'
`$env:DATABASE_URL = 'sqlite:///$dbUrlPath'
Get-Content '$rootEnv' | Where-Object { `$_ -match '^[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object {
    `$name, `$value = `$_ -split '=', 2
    if (`$name.Trim() -ne 'DATABASE_URL') {
        Set-Item -Path ('Env:' + `$name.Trim()) -Value `$value
    }
}
"@

if ($webhookSecret) {
    $apiCommand += "`n`$env:STRIPE_WEBHOOK_SECRET = '$webhookSecret'"
}

$apiCommand += @"
& '$pythonExe' -m app seed-demo
& '$pythonExe' -m uvicorn app.main:app --host $ApiHost --port $ApiPort --reload
"@

$frontendCommand = @"
Set-Location '$frontendDir'
npm run dev -- --host $WebHost --port $WebPort
"@

Start-BackgroundProcess -Title "DBOps API ($ApiPort)" -CommandText $apiCommand
Start-BackgroundProcess -Title "DBOps Web ($WebPort)" -CommandText $frontendCommand

if ($stripeApiKey -and $stripeExe) {
    $listenerCommand = @"
`$stripeExe = '$stripeExe'
`$apiKey = '$stripeApiKey'
& `$stripeExe listen --api-key `$apiKey --forward-to http://localhost:$ApiPort/billing/webhook
"@
    Start-BackgroundProcess -Title "Stripe Listener -> $ApiPort" -CommandText $listenerCommand
    Write-Host "Started Stripe listener in background."
}
else {
    Write-Host "Stripe listener not started (missing stripe CLI or STRIPE_SECRET_KEY)."
}

Write-Host "Local dev stack started."
Write-Host ("- API: http://localhost:{0}" -f $ApiPort)
Write-Host ("- Web: http://localhost:{0}" -f $WebPort)
Write-Host "- Use: .\scripts\local_dev_stack.ps1 -Mode status"
Write-Host "- Stop: .\scripts\local_dev_stack.ps1 -Mode stop"
