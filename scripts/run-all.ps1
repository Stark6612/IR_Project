# 1-Click Launch Script for Agri-Doctor Robot (Windows Native)
# Starts both the Python FastAPI/WebSocket Telemetry Server and the React Dashboard

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "🚜 Launching Agri-Doctor Robot System on Windows 11..." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green

$CurrentDir = Get-Location
$env:PYTHONPATH = "$CurrentDir\robotics"

Write-Host "[1/2] Starting Python FastAPI & WebSocket Telemetry Server..." -ForegroundColor Cyan
$ServerJob = Start-Process python -ArgumentList "-m uvicorn server:app --host 127.0.0.1 --port 8000 --app-dir robotics" -PassThru -NoNewWindow

Start-Sleep -Seconds 2

Write-Host "[2/2] Starting React + TypeScript + Vite Dashboard..." -ForegroundColor Cyan
Set-Location "$CurrentDir\dashboard"
npm run dev

# Cleanup when terminated
Stop-Process -Id $ServerJob.Id -ErrorAction SilentlyContinue
