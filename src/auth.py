"""
Authentication utilities: password hashing and JWT token handling.

Uses bcrypt directly instead of passlib — passlib is unmaintained and
incompatible with bcrypt >= 4.1 (missing __about__ attribute).
"""
from datetime import datetime, timedelta, timezone
import uuid

import bcrypt
from jose import JWTError, jwt

from src.config import settings

_REVOKED_JTI: set[str] = set()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str | int, role: str, organization_id: int) -> str:
    """Create a signed JWT for the given user id, role, and organization."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(subject),
        "role": role,
        "org": organization_id,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT. Raises JWTError on failure."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )


def revoke_token(token: str) -> None:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_exp": False, "verify_aud": False, "verify_iss": False},
        )
        jti = payload.get("jti")
        if isinstance(jti, str) and jti:
            _REVOKED_JTI.add(jti)
    except JWTError:
        return


def is_token_revoked(payload: dict) -> bool:
    jti = payload.get("jti")
    return isinstance(jti, str) and jti in _REVOKED_JTI
