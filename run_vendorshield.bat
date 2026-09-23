@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Project environment is missing. Run START_VENDORSHIELD.bat first.
  pause
  exit /b 1
)
if not exist "backend\app\workflow.py" (
  echo Required file backend\app\workflow.py is missing.
  echo Extract the complete upgraded ZIP again.
  pause
  exit /b 1
)
if not exist "data\vendorshield.db" (
  echo Database missing. Run: .venv\Scripts\python.exe scripts\build_database.py
  pause
  exit /b 1
)
".venv\Scripts\python.exe" run_all.py
endlocal
