@echo off
setlocal
cd /d "%~dp0"
title VendorShield - Procurement Risk Intelligence
color 0B

if not exist ".venv\Scripts\python.exe" (
    echo ================================================================
    echo  First-time setup required
    echo ================================================================
    echo Creating the project environment and installing dependencies...
    echo This is required only once.
    echo.
    call setup_windows.bat
    if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" run_all.py
endlocal
