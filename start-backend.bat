@echo off
REM Script to start Heritage Backend API
echo Starting Heritage Backend API...
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Start backend server
echo Backend will run on http://127.0.0.1:8000
echo API endpoints: http://localhost:8000/api
echo.
python -m uvicorn apps.backend.app:app --host 127.0.0.1 --port 8000 --reload
