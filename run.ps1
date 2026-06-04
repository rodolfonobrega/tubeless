#Requires -Version 5.1
param([string]$Cmd = "help")

$ROOT        = $PSScriptRoot

function step([string]$svc, [string]$msg) {
    Write-Host ("[$svc] " + $msg)
}

function Wait-Backend {
    step "backend" "waiting for http://127.0.0.1:8000..."
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($r.StatusCode -eq 200) { step "backend" "ready"; return $true }
        } catch {}
    }
    step "backend" "ERROR: did not start in time. Check Docker logs with: .\run.ps1 logs"
    return $false
}

function Start-Docker {
    step "docker" "checking if Docker daemon is running..."
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        docker ps -q 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        step "docker" "waiting for Docker daemon to initialize..."
        Start-Sleep -Seconds 2
    }
    if (-not $ready) {
        step "docker" "ERROR: Docker daemon is not running. Please open Docker Desktop and wait for the engine to start."
        exit 1
    }

    step "docker" "starting postgres + backend + frontend..."
    docker compose -f (Join-Path $ROOT "docker-compose.yml") up -d
    if ($LASTEXITCODE -ne 0) {
        step "docker" "ERROR: failed to start docker containers"
        exit 1
    }
}

function Stop-Docker {
    step "docker" "stopping containers..."
    docker compose -f (Join-Path $ROOT "docker-compose.yml") down
    step "docker" "stopped"
}

function cmd-up {
    Start-Docker
    Wait-Backend
    Write-Host ""
    Write-Host "  Frontend : http://localhost:3000"
    Write-Host "  Backend  : http://localhost:8000"
    Write-Host "  API docs : http://localhost:8000/docs"
    Write-Host ""
    Write-Host "  Stop : .\run.ps1 down"
    Write-Host "  Logs : .\run.ps1 logs"
}

function cmd-down {
    Stop-Docker
}

function cmd-status {
    docker compose -f (Join-Path $ROOT "docker-compose.yml") ps
}

function cmd-logs {
    docker compose -f (Join-Path $ROOT "docker-compose.yml") logs -f
}

switch ($Cmd) {
    "up"      { cmd-up }
    "down"    { cmd-down }
    "restart" { cmd-down; cmd-up }
    "status"  { cmd-status }
    "logs"    { cmd-logs }
    default {
        Write-Host "Usage: .\run.ps1 [up|down|restart|status|logs]"
        Write-Host ""
        Write-Host "  up       starts everything (postgres, backend, frontend) inside Docker"
        Write-Host "  down     stops and removes all containers"
        Write-Host "  restart  down + up"
        Write-Host "  status   shows the status of the containers"
        Write-Host "  logs     follows logs for all containers"
    }
}
