"""
Security and Cryptography Utilities for AutoValue.
Provides robust bcrypt password hashing, JWT token management,
and cryptographically secure random share token generation.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import secrets
import bcrypt
import jwt

from .config import settings


ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt with a secure salt.
    Never stores plaintext passwords.
    """
    if not password:
        raise ValueError("Password cannot be empty")
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    Safely handles invalid or corrupted hashes.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_jwt_secret() -> str:
    """
    Get the configured JWT signing secret.
    Enforces strict secret requirements in production, failing startup/token creation
    if secret is missing or set to an insecure default.
    """
    secret = settings.AUTH_SECRET or settings.SECRET_KEY
    if not secret or secret in [
        "autovalue-dev-secret-key-do-not-use-in-prod-xyz-987654321",
        "fallback-secret-autovalue-token-signing",
        "secret",
        "changeme",
        "default_secret"
    ]:
        if settings.ENVIRONMENT.lower() == "production":
            raise ValueError("JWT signing secret (AUTH_SECRET or SECRET_KEY) is missing or using an insecure default in production.")
        return "autovalue-dev-secret-key-do-not-use-in-prod-xyz-987654321"
    return secret


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a signed JWT access token.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    if extra_claims:
        to_encode.update(extra_claims)

    secret = get_jwt_secret()
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token signature and expiration.
    Returns the decoded payload dict if valid, or None if expired/tampered.
    """
    secret = get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def generate_share_token(length_bytes: int = 32) -> str:
    """
    Generate a cryptographically secure, URL-safe random string for public report sharing.
    Example: 43+ characters with 256 bits of entropy.
    """
    return secrets.token_urlsafe(length_bytes)
