"""
FastAPI Dependencies for database sessions, authentication, and user verification.
Supports dual-mode auth: HTTP-only cookies (recommended for browsers) and Bearer header (for APIs/clients).
"""
from typing import Optional, Generator
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..core.config import settings
from ..core.security import decode_access_token
from ..models.user import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_token_from_request(
    request: Request,
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[str]:
    """
    Extract JWT auth token from Authorization Bearer header OR HTTP-only session cookie.
    """
    if bearer_auth and bearer_auth.credentials:
        return bearer_auth.credentials

    # Check session cookie
    cookie_token = request.cookies.get(settings.COOKIE_NAME)
    if cookie_token:
        return cookie_token

    return None


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(get_token_from_request)
) -> Optional[User]:
    """
    Returns the authenticated User if valid credentials are provided, or None if unauthenticated.
    """
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        return None

    return user


def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """
    Strict dependency enforcing authenticated user presence.
    Returns HTTP 401 if missing, expired, or invalid.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in with valid credentials.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return current_user
