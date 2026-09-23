#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT
sleep 3
python -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
