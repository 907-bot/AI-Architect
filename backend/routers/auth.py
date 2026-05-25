"""
Authentication API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import structlog

from backend.auth.jwt import (
    JWTHandler, SignUpRequest, LoginRequest, Token, UserResponse,
    hash_password, verify_password, TokenData, get_jwt_handler
)
from backend.database.models import User
from backend.database.client import db_client
from backend.config import settings

log = structlog.get_logger()
router = APIRouter()

# ── JWT handler ──────────────────────────────────────────────────────────────
jwt_handler = get_jwt_handler(
    secret_key=settings.jwt_secret,
    algorithm=settings.jwt_algorithm,
    expiry_minutes=settings.jwt_expire_minutes
)

# HTTPBearer reads the "Authorization: Bearer <token>" header correctly
_bearer = HTTPBearer(auto_error=False)


# ── DB dependency ─────────────────────────────────────────────────────────────

def get_db() -> Session:
    """Yield a DB session; raise 503 if database is unavailable."""
    if db_client.SessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable — auth endpoints require a database connection"
        )
    with db_client.SessionLocal() as session:
        yield session


# ── Auth dependency ───────────────────────────────────────────────────────────

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Verify JWT bearer token and return the authenticated User.
    Uses FastAPI's HTTPBearer so the Authorization header is read correctly.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data: TokenData = jwt_handler.verify_token(credentials.credentials)
    except Exception as e:
        log.warning("token_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")

    return user


# ── SIGNUP ────────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=UserResponse)
async def signup(request: SignUpRequest, db: Session = Depends(get_db)):
    log.info("signup_attempt", email=request.email, username=request.username)

    existing = db.query(User).filter(
        (User.email == request.email) | (User.username == request.username)
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Email or username already registered")

    try:
        user = User(
            email=request.email,
            username=request.username,
            password_hash=hash_password(request.password),
            full_name=request.full_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        log.info("signup_success", user_id=user.id)
        return UserResponse(id=str(user.id), email=user.email, username=user.username,
                            full_name=user.full_name, avatar_url=user.avatar_url,
                            is_admin=user.is_admin)
    except Exception as e:
        db.rollback()
        log.error("signup_error", error=str(e))
        raise HTTPException(status_code=500, detail="Signup failed")


# ── LOGIN ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    log.info("login_attempt", email=request.email)

    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive")

    try:
        access_token, expires = jwt_handler.create_access_token(
            user_id=str(user.id), email=user.email,
            username=user.username, is_admin=user.is_admin
        )
        refresh_token = jwt_handler.create_refresh_token(user_id=str(user.id))
        user.last_login = datetime.utcnow()
        db.commit()
        log.info("login_success", user_id=user.id)
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int((expires - datetime.utcnow()).total_seconds())
        )
    except Exception as e:
        log.error("login_error", error=str(e))
        raise HTTPException(status_code=500, detail="Login failed")


# ── REFRESH ───────────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    try:
        user_id = jwt_handler.verify_refresh_token(refresh_token)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        access_token, expires = jwt_handler.create_access_token(
            user_id=str(user.id), email=user.email,
            username=user.username, is_admin=user.is_admin
        )
        log.info("token_refreshed", user_id=user.id)
        return Token(access_token=access_token,
                     expires_in=int((expires - datetime.utcnow()).total_seconds()))
    except HTTPException:
        raise
    except Exception as e:
        log.error("token_refresh_error", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# ── CURRENT USER ──────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse(id=str(user.id), email=user.email, username=user.username,
                        full_name=user.full_name, avatar_url=user.avatar_url,
                        is_admin=user.is_admin)


# ── LOGOUT ────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(user: User = Depends(get_current_user)):
    log.info("logout", user_id=user.id)
    return {"status": "logged_out"}


# ── HEALTH ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def auth_health():
    return {"status": "ok", "service": "auth",
            "database": "connected" if db_client.health_check() else "unavailable"}
