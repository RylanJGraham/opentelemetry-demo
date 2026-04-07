# React Native Explorer  One-time Setup Script
# Run this once to set up the environment

Write-Host "`n React Native Explorer  Setup" -ForegroundColor Cyan
Write-Host "=================================`n"

$ErrorActionPreference = "Continue"
$rootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $rootDir

#  Check prerequisites 

Write-Host " Checking prerequisites..." -ForegroundColor Yellow

# Node.js
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host " Node.js not found. Please install Node.js 18 or newer" -ForegroundColor Red
    exit 1
}
$nodeVersion = node --version
Write-Host "   Node.js $nodeVersion" -ForegroundColor Green

# Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host " Python not found. Please install Python 3.10 or newer" -ForegroundColor Red
    exit 1
}
$pyVersion = python --version
Write-Host "   $pyVersion" -ForegroundColor Green

# ADB
$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) {
    Write-Host "  adb not found in PATH. Make sure Android SDK Platform Tools are installed." -ForegroundColor Yellow
    Write-Host "    Set ANDROID_HOME and add platform-tools to PATH." -ForegroundColor Yellow
} else {
    Write-Host "   adb found" -ForegroundColor Green
    # Check for emulator
    $devices = adb devices 2>&1 | Select-String "emulator"
    if ($devices) {
        Write-Host "   Android emulator detected" -ForegroundColor Green
    } else {
        Write-Host "    No Android emulator running. Start one before running the agent." -ForegroundColor Yellow
    }
}

#  Create Python virtual environment 

Write-Host "`n Setting up Python environment..." -ForegroundColor Yellow

if (-not (Test-Path "venv")) {
    Write-Host "  Creating virtual environment..."
    python -m venv venv
}

# Activate and install
Write-Host "  Installing Python dependencies..."
& ".\venv\Scripts\pip.exe" install -r requirements.txt --quiet

Write-Host "   Python dependencies installed" -ForegroundColor Green

#  Install Web UI dependencies 

Write-Host "`n Setting up Web UI..." -ForegroundColor Yellow
Push-Location web
npm install --silent 2>$null
Pop-Location
Write-Host "   Web UI dependencies installed" -ForegroundColor Green

#  Create storage directories 

Write-Host "`n Creating storage directories..." -ForegroundColor Yellow
$dirs = @("storage\screenshots", "storage\stories", "storage\logs")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Host "   Storage directories created" -ForegroundColor Green

#  Check API Key 

Write-Host "`n Checking API key..." -ForegroundColor Yellow
if (Test-Path ".env") {
    $envContent = Get-Content ".env" | Where-Object { $_ -match "OPENROUTER_API_KEY" }
    if ($envContent) {
        Write-Host "   OPENROUTER_API_KEY found in .env" -ForegroundColor Green
    } else {
        Write-Host "    OPENROUTER_API_KEY not found in .env" -ForegroundColor Yellow
        Write-Host "     Add: OPENROUTER_API_KEY=sk-or-..." -ForegroundColor Yellow
    }
} else {
    Write-Host "    No .env file found" -ForegroundColor Yellow
    Write-Host "     Create .env with: OPENROUTER_API_KEY=sk-or-..." -ForegroundColor Yellow
}

#  Done 

Write-Host "`n Setup complete!" -ForegroundColor Cyan
Write-Host "   Run '.\scripts\start.ps1' to start the explorer.`n"
