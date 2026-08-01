import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings


# ── Password ──────────────────────────────────────────────────────────────────
# Using bcrypt directly — passlib is incompatible with bcrypt>=4.0 on Python 3.11.
# bcrypt has a hard 72-byte limit; we slice before encoding to stay safe.

def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


# ── OTP ───────────────────────────────────────────────────────────────────────

def generate_otp() -> str:
    """6-digit OTP."""
    return str(secrets.randbelow(900000) + 100000)


def hash_otp(otp: str) -> str:
    """Store SHA-256 of OTP, never plaintext."""
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp(plain_otp: str, stored_hash: str) -> bool:
    return hash_otp(plain_otp) == stored_hash


# ── JWT Access Tokens ──────────────────────────────────────────────────────────

def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises JWTError if invalid/expired."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


# ── Refresh Tokens ────────────────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """Opaque 64-byte hex token stored as hash."""
    return secrets.token_hex(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_token_expires() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


# ── Reset Tokens ──────────────────────────────────────────────────────────────

def generate_reset_token() -> str:
    return secrets.token_hex(32)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ── FastAPI Dependency ────────────────────────────────────────────────────────

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db

bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
):
    from app.models.auth import Auth

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(Auth).where(Auth.id == user_id, Auth.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_exception
    return user


async def get_current_verified_user(user=Depends(get_current_user)):
    # Email verification is optional for now (MVP) — don't block app access.
    # New signups auto-set email_verified=True; this guard is kept as a named
    # dependency so it can be tightened later without touching all routers.
    return user
