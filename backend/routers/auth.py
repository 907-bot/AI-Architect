"""
Authentication API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
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

# JWT handler
jwt_handler = get_jwt_handler(
    secret_key=settings.jwt_secret,
    algorithm=settings.jwt_algorithm,
    expiry_minutes=settings.jwt_expire_minutes
)


def get_db() -> Session:
    """Dependency injection for database"""
    with db_client.SessionLocal() as session:
        yield session


def get_current_user(
    authorization: str = None,
    db: Session = Depends(get_db)
) -> User:
    """Verify JWT and return current user"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme"
            )
        
        # Verify token
        token_data = jwt_handler.verify_token(token)
        
        # Fetch user from database
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return user
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    except Exception as e:
        log.error("token_verification_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# =====================================================
# SIGNUP
# =====================================================

@router.post("/signup", response_model=UserResponse)
async def signup(request: SignUpRequest, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    log.info("signup_attempt", email=request.email, username=request.username)
    
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == request.email) | (User.username == request.username)
    ).first()
    
    if existing_user:
        log.warning("signup_user_exists", email=request.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered"
        )
    
    try:
        # Create new user
        user = User(
            email=request.email,
            username=request.username,
            password_hash=hash_password(request.password),
            full_name=request.full_name
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        log.info("signup_success", user_id=user.id, email=user.email)
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            is_admin=user.is_admin
        )
        
    except Exception as e:
        db.rollback()
        log.error("signup_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signup failed"
        )


# =====================================================
# LOGIN
# =====================================================

@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login and get JWT tokens
    """
    log.info("login_attempt", email=request.email)
    
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        log.warning("login_failed", email=request.email, reason="invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        log.warning("login_failed", email=request.email, reason="inactive_account")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    try:
        # Generate tokens
        access_token, expires = jwt_handler.create_access_token(
            user_id=str(user.id),
            email=user.email,
            username=user.username,
            is_admin=user.is_admin
        )
        
        refresh_token = jwt_handler.create_refresh_token(user_id=str(user.id))
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        log.info("login_success", user_id=user.id, email=user.email)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int((expires - datetime.utcnow()).total_seconds())
        )
        
    except Exception as e:
        log.error("login_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


# =====================================================
# REFRESH TOKEN
# =====================================================

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        # Verify refresh token
        user_id = jwt_handler.verify_refresh_token(refresh_token)
        
        # Fetch user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new access token
        access_token, expires = jwt_handler.create_access_token(
            user_id=str(user.id),
            email=user.email,
            username=user.username,
            is_admin=user.is_admin
        )
        
        log.info("token_refreshed", user_id=user.id)
        
        return Token(
            access_token=access_token,
            expires_in=int((expires - datetime.utcnow()).total_seconds())
        )
        
    except Exception as e:
        log.error("token_refresh_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


# =====================================================
# GET CURRENT USER
# =====================================================

@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """
    Get current authenticated user profile
    """
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_admin=user.is_admin
    )


# =====================================================
# LOGOUT
# =====================================================

@router.post("/logout")
async def logout(user: User = Depends(get_current_user)):
    """
    Logout (client-side token invalidation)
    """
    log.info("logout", user_id=user.id, email=user.email)
    return {"status": "logged_out"}


# =====================================================
# HEALTH CHECK
# =====================================================

@router.get("/health")
async def auth_health():
    """Health check for auth service"""
    return {"status": "ok", "service": "auth"}


from datetime import datetime
