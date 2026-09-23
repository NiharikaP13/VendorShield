"""Create business-facing screenshots of the local VendorShield application."""
from __future__ import annotations

import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "screenshots"
HOST = "127.0.0.1"
BACKEND_PORT = 8000
CAPTURE_PORT = 8510
BACKEND_URL = f"http://{HOST}:{BACKEND_PORT}"
BASE_URL = f"http://{HOST}:{CAPTURE_PORT}/"
DB_PATH = ROOT / "data" / "vendorshield.db"


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((HOST, port)) == 0


def wait_for(url: str, timeout: int = 90) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=2).status_code < 500:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise RuntimeError(f"Service did not become ready: {url}")


def browser_candidates() -> list[Path]:
    values: list[Path] = []
    for base in [os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")]:
        if not base:
            continue
        root = Path(base)
        values.extend([
            root / "Google" / "Chrome" / "Application" / "chrome.exe",
            root / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        ])
    return values


def find_browser() -> Path:
    for path in browser_candidates():
        if path.exists():
            return path
    for name in ("chrome.exe", "msedge.exe", "chrome", "chromium", "microsoft-edge"):
        located = shutil.which(name)
        if located:
            return Path(located)
    raise RuntimeError("Google Chrome or Microsoft Edge was not found.")


def high_risk_case() -> str:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT purchase_id FROM transactions WHERE risk_level='High' ORDER BY fraud_probability DESC LIMIT 1"
        ).fetchone()
    if not row:
        raise RuntimeError("No High-risk transaction is available for the case screenshot.")
    return str(row[0])


def target_url(**params: str) -> str:
    return BASE_URL + ("?" + urlencode(params) if params else "")


def spawn(command: list[str], env: dict[str, str]) -> subprocess.Popen:
    kwargs: dict[str, object] = {"cwd": ROOT, "env": env, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(command, **kwargs)


def stop_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()


def capture(browser: Path, filename: str, url: str, wait_ms: int = 16000) -> None:
    output = OUT / filename
    with tempfile.TemporaryDirectory(prefix="vendorshield-capture-") as profile:
        command = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--disable-extensions",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1600,1000",
            "--force-device-scale-factor=1",
            f"--virtual-time-budget={wait_ms}",
            f"--user-data-dir={profile}",
            f"--screenshot={output}",
            url,
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        if result.returncode != 0 or not output.exists():
            message = result.stderr.strip() or result.stdout.strip() or "Browser screenshot command failed."
            raise RuntimeError(f"Could not capture {filename}: {message}")
    print(f"Created {filename}")


def main() -> int:
    backend: subprocess.Popen | None = None
    frontend: subprocess.Popen | None = None
    env = os.environ.copy()
    env["VENDORSHIELD_API_URL"] = BACKEND_URL
    env["VENDORSHIELD_CAPTURE_MODE"] = "1"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"

    try:
        if port_open(BACKEND_PORT):
            wait_for(f"{BACKEND_URL}/health", 10)
        else:
            backend = spawn([
                sys.executable, "-m", "uvicorn", "backend.app.main:app",
                "--host", HOST, "--port", str(BACKEND_PORT), "--log-level", "warning",
            ], env)
            wait_for(f"{BACKEND_URL}/health", 120)

        if port_open(CAPTURE_PORT):
            raise RuntimeError(f"Port {CAPTURE_PORT} is already in use. Close that application and try again.")
        frontend = spawn([
            sys.executable, "-m", "streamlit", "run", "frontend/app.py",
            "--server.address", HOST, "--server.port", str(CAPTURE_PORT),
            "--server.headless", "true", "--browser.gatherUsageStats", "false",
        ], env)
        wait_for(BASE_URL, 120)

        browser = find_browser()
        case_id = high_risk_case()
        OUT.mkdir(exist_ok=True)
        pages = [
            ("00_Login.png", target_url(), 9000),
            ("01_Command_Center.png", target_url(capture="1", page="overview"), 18000),
            ("02_Transaction_Review.png", target_url(capture="1", page="transactions"), 18000),
            ("03_Transaction_Case_File.png", target_url(capture="1", page="transactions", case=case_id, focus="case"), 22000),
            ("04_Supplier_Intelligence.png", target_url(capture="1", page="suppliers"), 18000),
            ("05_New_Transaction_Assessment.png", target_url(capture="1", page="assessment"), 16000),
        ]
        for filename, url, wait_ms in pages:
            capture(browser, filename, url, wait_ms)

        print(f"\nScreenshots saved to: {OUT}")
        try:
            os.startfile(OUT)  # type: ignore[attr-defined]
        except Exception:
            pass
        return 0
    finally:
        stop_process(frontend)
        stop_process(backend)


if __name__ == "__main__":
    raise SystemExit(main())
