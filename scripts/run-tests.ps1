# Automated Test Suite Runner for Agri-Doctor Robot

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "🧪 Running Agri-Doctor Robot Verification Test Suite..." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green

$CurrentDir = Get-Location
$env:PYTHONPATH = "$CurrentDir\robotics"

python -m pytest -v --tb=short
