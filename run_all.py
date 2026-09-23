"""One-click launcher for the VendorShield application.

Starts FastAPI and Streamlit from one console window, opens the browser,
and stops child services together when Ctrl+C is pressed.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
BACKEND_PORT = 8000
DASHBOARD_PORT = 8501
BACKEND_URL = f"http://{HOST}:{BACKEND_PORT}"
DASHBOARD_URL = f"http://{HOST}:{DASHBOARD_PORT}"


def port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((HOST, port)) == 0


def is_vendorshield_backend() -> bool:
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=2)
        if not response.ok:
            return False
        payload = response.json()
        return str(payload.get("status", "")).lower() in {"ok", "healthy"}
    except (requests.RequestException, ValueError):
        return False


def wait_for_url(url: str, timeout_seconds: int = 90) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=2).status_code < 500:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def spawn(command: list[str], env: dict[str, str]) -> subprocess.Popen:
    kwargs: dict[str, object] = {
        "cwd": ROOT,
        "env": env,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(command, **kwargs)


def stop_process(process: Optional[subprocess.Popen]) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            process.terminate()
            process.wait(timeout=8)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def main() -> int:
    os.chdir(ROOT)
    env = os.environ.copy()
    env["VENDORSHIELD_API_URL"] = BACKEND_URL
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"

    backend_process: Optional[subprocess.Popen] = None
    frontend_process: Optional[subprocess.Popen] = None
    reused_backend = False

    print("=" * 68)
    print(" VendorShield - Procurement Risk Intelligence")
    print("=" * 68)

    try:
        if port_is_open(BACKEND_PORT):
            if is_vendorshield_backend():
                reused_backend = True
                print("[OK] VendorShield backend is already running on port 8000.")
            else:
                print("[ERROR] Port 8000 is being used by another application.")
                print("Close that application, then run START_VENDORSHIELD.bat again.")
                input("Press Enter to close...")
                return 1
        else:
            print("[1/2] Starting secured FastAPI backend...")
            backend_process = spawn(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "backend.app.main:app",
                    "--host",
                    HOST,
                    "--port",
                    str(BACKEND_PORT),
                    "--log-level",
                    "warning",
                ],
                env,
            )
            if not wait_for_url(f"{BACKEND_URL}/health", 120):
                raise RuntimeError("Backend did not become ready within 120 seconds.")
            print("[OK] Backend ready.")

        if port_is_open(DASHBOARD_PORT):
            print("[OK] Dashboard is already running on port 8501.")
        else:
            print("[2/2] Starting Streamlit auditor dashboard...")
            frontend_process = spawn(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "frontend/app.py",
                    "--server.address",
                    HOST,
                    "--server.port",
                    str(DASHBOARD_PORT),
                    "--server.headless",
                    "true",
                    "--browser.gatherUsageStats",
                    "false",
                ],
                env,
            )
            if not wait_for_url(DASHBOARD_URL, 120):
                raise RuntimeError("Dashboard did not become ready within 120 seconds.")
            print("[OK] Dashboard ready.")

        print()
        print(f"Dashboard : {DASHBOARD_URL}")
        print(f"API docs  : {BACKEND_URL}/docs")
        print("Login     : auditor1 / demo-password")
        print()
        print("The browser is opening automatically.")
        print("Keep this window open while VendorShield is running.")
        print("Press Ctrl+C here to stop the application.")
        open_url = os.environ.get("VENDORSHIELD_OPEN_URL", DASHBOARD_URL)
        webbrowser.open(open_url)

        while True:
            if frontend_process is not None and frontend_process.poll() is not None:
                raise RuntimeError("Dashboard process stopped unexpectedly.")
            if backend_process is not None and backend_process.poll() is not None:
                raise RuntimeError("Backend process stopped unexpectedly.")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping VendorShield...")
        return 0
    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        print("Review the message above, then run START_VENDORSHIELD.bat again.")
        input("Press Enter to close...")
        return 1
    finally:
        stop_process(frontend_process)
        if not reused_backend:
            stop_process(backend_process)
        print("VendorShield stopped.")


if __name__ == "__main__":
    raise SystemExit(main())
