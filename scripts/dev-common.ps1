# Shared helpers for KrowLive dev scripts
# Dot-source from start-backend.ps1 / start-frontend.ps1

function Stop-PortListeners {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $connections = @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    )
    if (-not $connections) {
        return
    }

    $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        if ($procId -and $procId -ne 0) {
            Write-Host "Stopping PID $procId on port $Port..."
            taskkill /PID $procId /T /F 2>$null | Out-Null
        }
    }
    Start-Sleep -Milliseconds 800
}

function Stop-KrowBackendOnPort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    Stop-PortListeners -Port $Port

    # Orphaned uvicorn / multiprocessing.spawn workers (--reload on Windows)
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -match 'app\.main:app' -and
            ($_.CommandLine -match 'uvicorn' -or $_.CommandLine -match 'multiprocessing\.spawn')
        } |
        ForEach-Object {
            Write-Host "Stopping orphaned backend worker PID $($_.ProcessId)..."
            taskkill /PID $_.ProcessId /T /F 2>$null | Out-Null
        }
}

function Stop-KrowFrontendOnPort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    Stop-PortListeners -Port $Port

    Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'next dev' } |
        ForEach-Object {
            Write-Host "Stopping orphaned Next.js dev PID $($_.ProcessId)..."
            taskkill /PID $_.ProcessId /T /F 2>$null | Out-Null
        }
}

function Ensure-OllamaRunning {
    param(
        [string]$BaseUrl = "http://localhost:11434"
    )

    try {
        $response = Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "Ollama is already running at $BaseUrl"
            return
        }
    } catch {
        # fall through to start
    }

    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollama) {
        Write-Warning "Ollama not found on PATH - install from https://ollama.com or start manually."
        return
    }

    Write-Host "Starting Ollama server in background..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden

    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        try {
            $check = Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($check.StatusCode -eq 200) {
                Write-Host "Ollama started at $BaseUrl"
                return
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    Write-Warning "Ollama did not respond at $BaseUrl within 15s - enrichment may fall back to heuristics."
}
