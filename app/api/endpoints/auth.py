from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models.database import User
from app.schemas.auth import UserSignup, UserLogin, TokenResponse, UserResponse, RefreshRequest
from app.services.auth import auth_service
from app.services.jwt import create_access_token, create_refresh_token, decode_refresh_token

router = APIRouter()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: UserSignup, db: Session = Depends(get_db)):
    """Register a new account. Returns the created user (no token — user must log in)."""
    existing = auth_service.get_user_by_username(payload.username, db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken.",
        )
    user = auth_service.create_user(payload.username, payload.password, db)
    return UserResponse(id=user.id, username=user.name)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate and return both tokens:
    - access_token  : short-lived (60 min), sent with every API request
    - refresh_token : long-lived (7 days), used only to silently renew the access token
    """
    user = auth_service.authenticate_user(payload.username, payload.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(user.id, user.name),
        refresh_token=create_refresh_token(user.id, user.name),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(payload: RefreshRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Called automatically by the Flask frontend whenever it receives a 401,
    so the user is never forced to log in again unless the refresh token
    itself expires (7 days of total inactivity).
    """
    token_payload = decode_refresh_token(payload.refresh_token)

    user = db.query(User).filter(User.id == uuid.UUID(token_payload["sub"])).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists.",
        )

    return TokenResponse(
        access_token=create_access_token(user.id, user.name),
        refresh_token=create_refresh_token(user.id, user.name),
    )
