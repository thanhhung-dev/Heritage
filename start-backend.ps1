# Heritage Backend API Startup Script
Write-Host "Starting Heritage Backend API..." -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path ".venv/Scripts/Activate.ps1")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment (for current session context)
Write-Host "Using virtual environment: .venv" -ForegroundColor Green

# Start backend server
Write-Host "Backend will run on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "API endpoints: http://localhost:8000/api" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn apps.backend.app:app --host 127.0.0.1 --port 8000 --reload
