#!/usr/bin/env pwsh
# React Native Explorer v2.0 - Startup Script

param(
    [switch]$SkipAgent,
    [switch]$SkipUI,
    [switch]$ClearData
)

$ErrorActionPreference = "Stop"

Write-Host @"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        React Native Explorer v2.0                            ║
║        Next.js + FastAPI + MCP                               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

# Clear data if requested
if ($ClearData) {
    Write-Host "🗑️  Clearing storage..." -ForegroundColor Yellow
    Remove-Item -Path "storage/*" -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path "storage/screenshots" -Force | Out-Null
}

# Ensure storage directory exists
New-Item -ItemType Directory -Path "storage/screenshots" -Force | Out-Null

$agentJob = $null

# Start Agent Server
try {
    if (-not $SkipAgent) {
        Write-Host "🔧 Starting Agent Server on http://127.0.0.1:5100..." -ForegroundColor Green
        
        # Check Python dependencies
        $missingDeps = @()
        $deps = @("fastapi", "uvicorn", "aiosqlite", "mcp", "pydantic")
        foreach ($dep in $deps) {
            $result = python -c "import $dep" 2>&1
            if ($LASTEXITCODE -ne 0) {
                $missingDeps += $dep
            }
        }
        
        if ($missingDeps.Count -gt 0) {
            Write-Host "📦 Installing missing dependencies: $($missingDeps -join ', ')" -ForegroundColor Yellow
            pip install -r agent-server/requirements.txt
        }
        
        # Start agent in background job
        $agentJob = Start-Job -ScriptBlock {
            Set-Location $using:PWD\agent-server
            python -m src.main
        }
        
        # Wait for agent to be ready
        Write-Host "⏳ Waiting for agent to be ready..." -ForegroundColor Gray
        $ready = $false
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 1
            try {
                $response = Invoke-WebRequest -Uri "http://127.0.0.1:5100/api/health" -UseBasicParsing -TimeoutSec 2
                if ($response.StatusCode -eq 200) {
                    $ready = $true
                    break
                }
            } catch {
                Write-Host "." -NoNewline -ForegroundColor Gray
            }
        }
        Write-Host ""
        
        if (-not $ready) {
            throw "Agent server failed to start"
        }
        Write-Host "✅ Agent Server ready!" -ForegroundColor Green
    }
    
    # Start Frontend
    if (-not $SkipUI) {
        Write-Host "🌐 Starting Next.js Frontend on http://localhost:3000..." -ForegroundColor Green
        
        # Check if node_modules exists
        if (-not (Test-Path "frontend/node_modules")) {
            Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Yellow
            Set-Location frontend
            npm install
            Set-Location ..
        }
        
        Write-Host @"

═══════════════════════════════════════════════════════════════

   🚀 Explorer v2.0 is running!

   Agent Server: http://127.0.0.1:5100
   Frontend:     http://localhost:3000

   Press Ctrl+C to stop

═══════════════════════════════════════════════════════════════

"@ -ForegroundColor Cyan
        
        # Start frontend (this blocks)
        Set-Location frontend
        npm run dev
    }
    
} finally {
    # Cleanup
    if ($agentJob) {
        Write-Host "`n🛑 Stopping Agent Server..." -ForegroundColor Yellow
        Stop-Job $agentJob -ErrorAction SilentlyContinue
        Remove-Job $agentJob -ErrorAction SilentlyContinue
    }
    
    Write-Host "✨ Cleanup complete" -ForegroundColor Green
}
