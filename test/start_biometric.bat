@echo off
REM Start Biometric Integration Script
REM This script connects to ZK K40 device and processes attendance

setlocal enabledelayedexpansion

echo.
echo ======================================
echo   FDPP EMS - Biometric Integration
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
echo Verifying required libraries...

python -c "from zk import ZK" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Installing pyzk library...
    pip install pyzk
)

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Installing requests library...
    pip install requests
)

echo ✅ All libraries ready
echo.
echo ======================================
echo Biometric Device Integration Starting
echo ======================================
echo.
echo Logs will be saved to: biometric_integration.log
echo Press Ctrl+C to stop
echo.

python biometric_integration.py

if errorlevel 1 (
    echo.
    echo ❌ Biometric script failed
    echo Check biometric_integration.log for details
    pause
    exit /b 1
)

pause
