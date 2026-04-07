# React Native Explorer Start Script
# Starts both the Vite Web UI (port 3000) and Python API (port 5100)

Write-Host "`n React Native Explorer Agent" -ForegroundColor Cyan
Write-Host "================================`n"

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $rootDir

# Check venv exists 
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "  Virtual environment not found. Running setup first..." -ForegroundColor Yellow
    & ".\scripts\setup.ps1"
}

# 🔧 Cleanup any old processes on Port 3000 or 5100 (zombies)
Write-Host " Checking for zombie processes on ports 3000 and 5100..." -ForegroundColor Yellow
$ports = @(3000, 5100)
foreach ($port in $ports) {
    $procId = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue).OwningProcess
    if ($procId) {
        Write-Host "   Killing process $procId on port $port..." -ForegroundColor Yellow
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}

# 1. Start the Unified Explorer process
Write-Host " Starting Unified Explorer (UI + Agent)..." -ForegroundColor Yellow
Write-Host "   Open http://localhost:5100 in your browser`n" -ForegroundColor Cyan

try {
    # 🔧 Run the unified server in the foreground. 
    # It now serves the UI built in the previous step.
    & ".\venv\Scripts\python.exe" -m agent --ui-only
} finally {
    Write-Host "`n Cleaning up..." -ForegroundColor Yellow
    Write-Host " All processes stopped.`n" -ForegroundColor Green
}
