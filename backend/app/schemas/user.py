"""
Pydantic contracts for user authentication, registration, profiles, and account management.
"""
from typing import Optional
from datetime import datetime
import re
from pydantic import BaseModel, Field, field_validator, ConfigDict


class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User's unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password (minimum 8 characters)")
    full_name: Optional[str] = Field(None, max_length=128, description="User's full name")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Email must be a valid string")
        v = v.strip().lower()
        # Basic format check
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        if len(v.strip()) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "analyst@example.com",
                "password": "SecurePassword123!",
                "full_name": "Rohan Sharma"
            }
        }
    )


class UserLoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Email must be a valid string")
        return v.strip().lower()


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserUpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=128)
