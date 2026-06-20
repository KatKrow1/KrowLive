# Start KrowLive backend (uvicorn) on a clean port.
#
# Usage:
#   .\scripts\start-backend.ps1              # stable, no reload (recommended for testing)
#   .\scripts\start-backend.ps1 -Reload      # auto-reload on file changes (active dev only)
#   .\scripts\start-backend.ps1 -Port 8002
#
# Stop with Ctrl+C in THIS window. The finally block cleans up the process tree.

param(
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "dev-common.ps1")

$Root = Split-Path -Parent $ScriptDir
$Backend = Join-Path $Root "backend"
$Uvicorn = Join-Path $Backend "venv\Scripts\uvicorn.exe"

if (-not (Test-Path $Uvicorn)) {
    Write-Error "Backend venv not found. Run: cd backend; python -m venv venv; .\venv\Scripts\pip install -r requirements.txt"
}

Write-Host "== KrowLive backend =="
Write-Host "Clearing anything on port $Port..."
Stop-KrowBackendOnPort -Port $Port

Set-Location $Backend

$uvicornArgs = @("app.main:app", "--host", "127.0.0.1", "--port", "$Port")
if ($Reload) {
    $uvicornArgs += "--reload"
    Write-Host "Mode: --reload (use only while actively editing Python; can orphan workers on Windows if this terminal is killed)"
} else {
    Write-Host "Mode: no reload (recommended for testing and demos)"
}

Write-Host "URL: http://127.0.0.1:$Port"
Write-Host "Press Ctrl+C to stop.`n"

try {
    & $Uvicorn @uvicornArgs
    exit $LASTEXITCODE
} finally {
    Write-Host "`nCleaning up backend processes on port $Port..."
    Stop-KrowBackendOnPort -Port $Port
}
