# React Native Explorer — Start Script
# Starts both the Web UI and the Python exploration agent

Write-Host "`n🚀 React Native Explorer Agent" -ForegroundColor Cyan
Write-Host "================================`n"

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $rootDir

# ── Check venv exists ─────────────────────────────────────────────

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "⚠️  Virtual environment not found. Running setup first..." -ForegroundColor Yellow
    & ".\scripts\setup.ps1"
}

# ── Start Web UI in background ────────────────────────────────────

Write-Host "🌐 Starting Web UI at http://localhost:3000..." -ForegroundColor Yellow

$webJob = Start-Job -ScriptBlock {
    param($rootDir)
    Set-Location "$rootDir\web"
    & npx vite --port 3000 --host 127.0.0.1
} -ArgumentList $rootDir

Write-Host "  ✅ Web UI started (Job ID: $($webJob.Id))" -ForegroundColor Green

# ── Wait a moment for web server to start ─────────────────────────

Start-Sleep -Seconds 3

# ── Start the Python agent ────────────────────────────────────────

Write-Host "`n🔍 Starting exploration agent..." -ForegroundColor Yellow
Write-Host "   (Press Ctrl+C to stop)`n"

try {
    & ".\venv\Scripts\python.exe" -m agent.explorer @args
} catch {
    Write-Host "`n⚠️  Agent stopped: $_" -ForegroundColor Yellow
} finally {
    # ── Cleanup ───────────────────────────────────────────────────

    Write-Host "`n🧹 Cleaning up..." -ForegroundColor Yellow
    Stop-Job -Job $webJob -ErrorAction SilentlyContinue
    Remove-Job -Job $webJob -Force -ErrorAction SilentlyContinue
    Write-Host "✅ All processes stopped.`n" -ForegroundColor Green
}
