@echo off
cd /d "%~dp0"
set VENDORSHIELD_API_URL=http://127.0.0.1:8000
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -m streamlit run frontend\app.py --server.port 8501
) else (
  python -m streamlit run frontend\app.py --server.port 8501
)
