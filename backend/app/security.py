"""Database-backed authentication and persistent sessions for VendorShield."""
from __future__ import annotations
import hashlib, hmac, os, secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from fastapi import Header, HTTPException, status
from backend.app import database

API_KEY = os.environ.get("VENDORSHIELD_API_KEY", "dev-api-key-change-me")
TOKEN_TTL_SECONDS = int(os.environ.get("VENDORSHIELD_SESSION_SECONDS", str(8*60*60)))

@dataclass(frozen=True)
class AuthContext:
    auditor_id: int
    username: str
    email: str
    role: str
    display_name: str

def hash_password(password: str, salt: bytes | None=None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return f"pbkdf2_sha256$210000${salt.hex()}${digest.hex()}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt_hex, expected = encoded.split("$", 3)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def validate_password(password: str) -> None:
    if len(password) < 8 or not any(c.isupper() for c in password) or not any(c.islower() for c in password) or not any(c.isdigit() for c in password):
        raise HTTPException(422, "Password must be at least 8 characters and include uppercase, lowercase, and a number.")

def register(name: str, email: str, password: str, department: str="", employee_id: str="") -> dict:
    validate_password(password)
    email = email.strip().lower()
    if "@" not in email:
        raise HTTPException(422, "Enter a valid email address.")
    username = email.split("@",1)[0]
    try:
        return database.create_auditor(username, name.strip(), email, hash_password(password), department.strip(), employee_id.strip())
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc

def issue_token(identifier: str, password: str) -> tuple[str, AuthContext]:
    user = database.find_auditor(identifier.strip().lower())
    if user is None or not verify_password(password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email/username or password.")
    token = secrets.token_urlsafe(40)
    expires = datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL_SECONDS)
    database.create_session(user["id"], token, expires.isoformat())
    database.update_last_login(user["id"])
    return token, AuthContext(user["id"], user["username"], user["email"], user["role"], user["display_name"])

def revoke_token(token: str) -> None:
    database.revoke_session(token)

async def require_auth(authorization: str | None=Header(default=None), x_api_key: str | None=Header(default=None)) -> AuthContext:
    if x_api_key and hmac.compare_digest(x_api_key, API_KEY):
        return AuthContext(0,"api-key","","admin","API Client")
    if authorization and authorization.lower().startswith("bearer "):
        token=authorization.split(" ",1)[1].strip()
        row=database.resolve_session(token)
        if row:
            return AuthContext(row["id"],row["username"],row["email"],row["role"],row["display_name"])
    raise HTTPException(status.HTTP_401_UNAUTHORIZED,"Your session is missing or expired. Please sign in again.")
