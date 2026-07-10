"""
auth.py - Simple JWT authentication for Kizlly.

Provides reviewer identity tracking: every approval/rejection
is tied to a specific authenticated user.
"""

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict

import jwt
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS

# ---------------------------------------------------------------------------
# In-memory user store (sufficient for hackathon demo)
# ---------------------------------------------------------------------------
_users: Dict[str, dict] = {}

# Pre-seed a demo reviewer account
_users["admin"] = {
    "username": "admin",
    "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
    "display_name": "Admin Reviewer",
    "created_at": datetime.utcnow().isoformat(),
}

security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Password hashing (simple SHA-256 for demo — use bcrypt in production)
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(password.encode()).hexdigest(),
        password_hash,
    )


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

def register_user(username: str, password: str, display_name: Optional[str] = None) -> dict:
    """Register a new reviewer account."""
    if username in _users:
        raise HTTPException(status_code=409, detail="Username already exists")

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user = {
        "username": username,
        "password_hash": _hash_password(password),
        "display_name": display_name or username,
        "created_at": datetime.utcnow().isoformat(),
    }
    _users[username] = user
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
        "exp": int((datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token."""
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

    if not username or username not in _users:
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
