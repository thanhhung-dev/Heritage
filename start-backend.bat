@echo off
REM Chay Heritage Backend API tren Windows.
REM Phai dung scripts\run-backend.py: uvicorn truc tiep se dat lai event loop ve
REM Proactor (mac dinh cua Windows) va psycopg async nem InterfaceError ngay query
REM dau tien. Script do cung doc BACKEND_PORT trong .env.

setlocal
cd /d "%~dp0"

set "CHAT_BACKEND_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%CHAT_BACKEND_PYTHON%" set "CHAT_BACKEND_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if not exist "%CHAT_BACKEND_PYTHON%" (
    echo [x] Khong thay .venv\Scripts\python.exe
    echo     Tao moi truong:  python -m venv .venv
    echo     Cai thu vien:    .venv\Scripts\pip install -r apps\backend\requirements.txt
    exit /b 1
)

echo Starting Heritage Backend API...
echo.

"%CHAT_BACKEND_PYTHON%" "%~dp0scripts\run-backend.py" %*
exit /b %errorlevel%
