@echo off
title Dayleaf Campus - Server Launcher
color 0B
echo ========================================================
echo               DAYLEAF TIMETABLE & CAMPUS
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] Starting Dayleaf Backend API (Port 8000)...
start "Dayleaf API" cmd /k "set PYTHONPATH=apps/api && apps\api\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Dayleaf Web UI (Port 3010)...
start "Dayleaf Web" cmd /k "cd apps\web && npm run dev -- -p 3010"

echo.
echo ========================================================
echo  Dayleaf is running!
echo  URL: http://127.0.0.1:3010
echo  Email: sushantprakash2003@gmail.com
echo  Password: Dayleaf@2026
echo ========================================================
echo.
pause
