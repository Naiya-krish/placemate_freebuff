from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import Role
from app.schemas.common import ORMModel


class RegisterRequest(BaseModel):
    college_code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    branch: str = Field(min_length=1, max_length=60)
    target_role: str = Field(default="Software Engineer", min_length=2, max_length=80)
    consent_notice: bool
    share_analytics: bool = False

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower().strip()

    @field_validator("college_code")
    @classmethod
    def uppercase_code(cls, value: str) -> str:
        return value.strip().upper()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    college_code: str | None = Field(default=None, max_length=32)


class UserOut(ORMModel):
    id: uuid.UUID
    college_id: uuid.UUID
    college_name: str | None = None
    email: EmailStr
    name: str
    role: Role
    branch: str | None = None
    target_role: str | None = None
    avatar_url: str | None = None
    xp: int
    streak_count: int
    consent_share_analytics: bool
    onboarding_complete: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class ConsentUpdate(BaseModel):
    share_analytics: bool
    policy_version: str | None = Field(default=None, max_length=20)


class OnboardingUpdate(BaseModel):
    branch: str = Field(min_length=1, max_length=60)
    target_role: str = Field(min_length=2, max_length=80)
    complete: bool = True


class DeleteAccountRequest(BaseModel):
    confirm: str = Field(pattern="^DELETE$")
    password: str | None = Field(default=None, max_length=128)
