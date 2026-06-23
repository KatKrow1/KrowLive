# Start KrowLive frontend (Next.js dev server) on a clean port.
#
# Usage:
#   .\scripts\start-frontend.ps1
#   .\scripts\start-frontend.ps1 -Port 3001
#
# Stop with Ctrl+C in THIS window.

param(
    [int]$Port = 3000
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "dev-common.ps1")

$Root = Split-Path -Parent $ScriptDir
$Frontend = Join-Path $Root "frontend"

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Error "Frontend dependencies not installed. Run: cd frontend; npm install"
}

Write-Host "== KrowLive frontend =="
Write-Host "Clearing anything on port $Port..."
Stop-KrowFrontendOnPort -Port $Port

Set-Location $Frontend

Write-Host "URL: http://localhost:$Port"
Write-Host "Press Ctrl+C to stop.`n"

try {
    npm run dev -- -p $Port
    exit $LASTEXITCODE
} finally {
    Write-Host "`nCleaning up frontend processes on port $Port..."
    Stop-KrowFrontendOnPort -Port $Port
}
