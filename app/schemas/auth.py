from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re
import uuid


# ──────────────────────────────────────────────
# Auth schemas
# ──────────────────────────────────────────────

class UserSignup(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=64)

    @field_validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ──────────────────────────────────────────────
# Task schemas
# ──────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=225)
    description: Optional[str] = Field(default=None, max_length=500)
    priority: str = Field(default='P3', pattern=r'^(P[1-5]|EOD)$')
    estimated_minutes: Optional[int] = Field(default=None, ge=1)


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    priority: str
    created_by_username: str

    # created_at is stored and returned as IST-aware datetime
    created_at: datetime

    # Original estimate set at task creation (never changes)
    estimated_minutes: Optional[int]

    # Computed on every API call:
    #   remaining_minutes = estimated_minutes - minutes_elapsed_since_creation
    #   Clamped to 0 (never goes negative). None when no estimate was given.
    remaining_minutes: Optional[int]

    # True when remaining_minutes == 0 AND task is not done yet
    is_time_up: bool

    is_done: bool

    model_config = {"from_attributes": True}
