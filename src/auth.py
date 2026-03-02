"""
Authentication utilities: password hashing and JWT token handling.

Uses bcrypt directly instead of passlib — passlib is unmaintained and
incompatible with bcrypt >= 4.1 (missing __about__ attribute).
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from src.config import settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str | int, role: str) -> str:
    """Create a signed JWT for the given user id and role."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
