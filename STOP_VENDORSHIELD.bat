@echo off
setlocal
for %%P in (8000 8501) do (
  for /f "tokens=5" %%A in ('netstat -aon ^| findstr ":%%P" ^| findstr "LISTENING"') do (
    taskkill /PID %%A /T /F >nul 2>&1
  )
)
echo VendorShield services stopped.
timeout /t 2 >nul
endlocal
