# Heritage Backend API Startup Script (Windows)
#
# Dung scripts/run-backend.py thay vi goi uvicorn truc tiep: uvicorn dat lai event
# loop policy ve Proactor (mac dinh cua Windows) va psycopg async nem
# InterfaceError ngay query DB dau tien. Script do cung doc BACKEND_PORT trong .env.
#
#   .\start-backend.ps1              # cong theo .env (mac dinh 8000)
#   .\start-backend.ps1 -Port 8001

param(
    [int]$Port = 0,
    [string]$HostAddress = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = Join-Path (Split-Path $PSScriptRoot -Parent) ".venv\Scripts\python.exe"
}
if (-not (Test-Path $python)) {
    Write-Host "ERROR: khong thay .venv\Scripts\python.exe" -ForegroundColor Red
    Write-Host "  python -m venv .venv" -ForegroundColor Yellow
    Write-Host "  .venv\Scripts\pip install -r apps\backend\requirements.txt" -ForegroundColor Yellow
    exit 1
}

$cliArgs = @((Join-Path $PSScriptRoot "scripts\run-backend.py"), "--host", $HostAddress)
if ($Port -gt 0) { $cliArgs += @("--port", "$Port") }

Write-Host "Starting Heritage Backend API..." -ForegroundColor Cyan
& $python @cliArgs
exit $LASTEXITCODE
