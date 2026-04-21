@echo off
REM Start Django Server with Daphne (FDPP EMS)
REM This file starts the Django server that handles API requests

setlocal enabledelayedexpansion

echo.
echo ======================================
echo   FDPP EMS - Django Server Startup
echo ======================================
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

echo ✅ Virtual environment activated
echo.
echo Starting Django server on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.
echo ======================================
echo.

cd fdpp_ems
daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application

if errorlevel 1 (
    echo.
    echo ❌ Server failed to start
    echo Check the error messages above
    pause
    exit /b 1
)

pause
