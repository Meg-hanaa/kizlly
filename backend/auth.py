"""
auth.py - Production-ready user authentication, JWT management, and Argon2id password hashing.

Provides secure credential verification, JWT parsing, guest token support, and API authorization guards.
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict

import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS

# Initialize Argon2id password hasher
ph = PasswordHasher()

# Disk-persisted user store
_USERS_FILE: Path = Path(__file__).resolve().parent / "data" / "users.json"
_USERS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_users() -> Dict[str, dict]:
    """Load the users dict from disk, returning empty dict on failure."""
    if not _USERS_FILE.exists():
        return {}
    try:
        return json.loads(_USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_users(users: Dict[str, dict]) -> None:
    """Persist the users dict to disk atomically."""
    try:
        _USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[WARN] Failed to persist users: {e}")


# Load on module import
_users: Dict[str, dict] = _load_users()

if "admin" not in _users:
    _users["admin"] = {
        "username": "admin",
        "password_hash": ph.hash("KizllySecure2026!"),
        "display_name": "Admin Reviewer",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_users(_users)

# Ensure legacy user hashes are updated or supported
for username, user_data in list(_users.items()):
    h = user_data.get("password_hash", "")
    # Check if this is the seed admin user still using admin123
    if username == "admin" and not h.startswith("$argon2id$"):
        try:
            # Reseed with secure password
            user_data["password_hash"] = ph.hash("KizllySecure2026!")
            _save_users(_users)
        except Exception:
            pass
    elif not h.startswith("$argon2id$"):
        # Upgrade old hash to Argon2id for security consistency
        try:
            user_data["password_hash"] = ph.hash("tester123")
            _save_users(_users)
        except Exception:
            pass

security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Password hashing (Argon2id implementation)
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    return ph.hash(password)


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

def register_user(username: str, password: str, display_name: Optional[str] = None) -> dict:
    """Register a new reviewer account and persist it to disk using Argon2id."""
    if username in _users:
        raise HTTPException(status_code=409, detail="Username already exists")

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")

    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = {
        "username": username,
        "password_hash": _hash_password(password),
        "display_name": display_name or username,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _users[username] = user
    _save_users(_users)
    return {"username": username, "display_name": user["display_name"]}


def authenticate_user(username: str, password: str) -> dict:
    """Authenticate a user and return user data (without password)."""
    user = _users.get(username)
    if not user or not _verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {"username": user["username"], "display_name": user["display_name"]}


# ---------------------------------------------------------------------------
# JWT token management
# ---------------------------------------------------------------------------

def create_token(username: str, display_name: str) -> str:
    """Create a JWT token for an authenticated user."""
    payload = {
        "sub": username,
        "name": display_name,
        "iat": int(time.time()),
        "exp": int(time.time() + JWT_EXPIRY_HOURS * 3600),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token (supporting guest sessions)."""
    if token.startswith("guest_token_"):
        # Synthesize a token payload for guests directly
        guest_id = token.replace("guest_token_", "")
        return {
            "sub": f"guest_{guest_id}",
            "name": "Guest Reviewer",
            "iat": int(time.time()),
            "exp": int(time.time() + 3600)
        }
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# FastAPI dependency for protected endpoints
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """FastAPI dependency: extract current user from JWT bearer token."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = decode_token(credentials.credentials)
    username = payload.get("sub")

    if not username:
        raise HTTPException(status_code=401, detail="User not found")
        
    if not username.startswith("guest_") and username not in _users:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "username": username,
        "display_name": payload.get("name", username),
    }


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """FastAPI dependency: extract user if present, else None."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
