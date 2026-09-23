@echo off
setlocal
cd /d "%~dp0"
title VendorShield - First Time Setup

if not exist "backend\app\workflow.py" (
  echo [ERROR] Required file backend\app\workflow.py is missing.
  echo You are running an incomplete or older project folder.
  echo Extract the complete VendorShield_Professional_Project_Upgraded_FIXED.zip again.
  pause
  exit /b 1
)

py -3.12 -c "import sys" >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON_CMD=py -3.12"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python was not found. Install Python 3.11 or 3.12 and try again.
    pause
    exit /b 1
  )
  set "PYTHON_CMD=python"
)

echo [1/4] Creating virtual environment...
if not exist ".venv\Scripts\python.exe" (
  %PYTHON_CMD% -m venv .venv
)
if errorlevel 1 goto :error

echo [2/4] Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [3/4] Installing tested project dependencies...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [4/4] Running end-to-end smoke test...
.venv\Scripts\python.exe tests\smoke_test.py
if errorlevel 1 goto :error

echo.
echo Setup complete.
echo From now on, double-click START_VENDORSHIELD.bat.
echo.
pause
exit /b 0

:error
echo.
echo Setup failed. Read the error above and run setup_windows.bat again.
pause
exit /b 1
