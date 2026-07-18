"""JWT token utilities — create and verify access tokens."""
from datetime import datetime, timedelta, timezone
import jwt
from core.config import settings


def create_access_token(data: dict, expires_delta: int | None = None) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data to encode (e.g. {"user_id": 1}).
        expires_delta: Seconds from now until expiry. If None, uses
            ACCESS_TOKEN_EXPIRE_MINUTES from settings.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + timedelta(seconds=expires_delta)
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Decode and verify a JWT token.

    Args:
        token: JWT string to verify.

    Returns:
        Decoded payload as a dict.

    Raises:
        jwt.PyJWTError: If token is invalid or expired.
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
