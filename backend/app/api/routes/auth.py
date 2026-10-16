"""
User Authentication and Profile API Routes.
Provides secure registration, login, logout, profile retrieval, and account deletion.
"""
from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.security import hash_password, verify_password, create_access_token
from ...db.session import get_db
from ...models.user import User
from ...schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    UserUpdateProfileRequest
)
from ..deps import get_current_user

logger = logging.getLogger("autovalue.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account"
)
def register_user(
    payload: UserRegisterRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Register a new user with a normalized email and bcrypt-hashed password.
    Returns an access token and sets a secure session cookie.
    """
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists."
        )

    hashed_pw = hash_password(payload.password)
    user = User(
        email=payload.email,
        password_hash=hashed_pw,
        full_name=payload.full_name,
        is_active=True,
        last_login_at=datetime.now(timezone.utc)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=user.id)

    # Set secure HTTP-only cookie
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )

    logger.info(f"New user registered successfully: user_id={user.id}")
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain session token"
)
def login_user(
    payload: UserLoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticate user credentials. Returns generic 401 error if email or password is invalid,
    preventing user enumeration.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=user.id)

    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )

    logger.info(f"User logged in successfully: user_id={user.id}")
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/logout",
    summary="Clear active authentication session"
)
def logout_user(response: Response):
    """
    Clear the session authentication cookie.
    """
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/"
    )
    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile"
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve profile details of the currently authenticated user.
    """
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile"
)
def update_user_profile(
    payload: UserUpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update profile details for current user.
    """
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip() or None
    
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.delete(
    "/me",
    summary="Permanently delete current user account and data"
)
def delete_user_account(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Self-service account deletion. Permanently cascades deletion of all user's
    saved valuations, bookmarks, and share tokens without affecting public datasets.
    """
    deleted_user_id = current_user.id
    db.delete(current_user)
    db.commit()

    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/"
    )
    logger.info(f"User account permanently deleted: user_id={deleted_user_id}")
    return {
        "message": "User account and all associated personal data have been permanently deleted."
    }
