@echo off
setlocal
cd /d "%~dp0"
title VendorShield - Capture Project Pages
if not exist ".venv\Scripts\python.exe" (
  echo First run setup_windows.bat before capturing screenshots.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" tools\capture_screenshots.py
if errorlevel 1 (
  echo.
  echo Screenshot capture failed. Review the message above.
  pause
)
endlocal
