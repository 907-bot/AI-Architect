"""
Authentication layer with JWT tokens
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
import bcrypt as _bcrypt
import structlog

log = structlog.get_logger()


# ---- Password utilities ----

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        return _bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ---- Schemas ----

class TokenData(BaseModel):
    user_id: str
    email: str
    username: str
    is_admin: bool = False


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class SignUpRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    is_admin: bool


# ---- JWT utilities ----

class JWTHandler:
    """JWT token generation and verification"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", expiry_minutes: int = 1440):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expiry_minutes = expiry_minutes
    
    def create_access_token(self, user_id: str, email: str, username: str, is_admin: bool = False) -> tuple[str, datetime]:
        """Create JWT access token"""
        expires = datetime.utcnow() + timedelta(minutes=self.expiry_minutes)
        payload = {
            "user_id": user_id,
            "email": email,
            "username": username,
            "is_admin": is_admin,
            "exp": expires,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            log.info("access_token_created", user_id=user_id, expires=expires)
            return token, expires
        except Exception as e:
            log.error("access_token_creation_failed", error=str(e))
            raise
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token (longer expiry)"""
        expires = datetime.utcnow() + timedelta(days=7)  # 7 days
        payload = {
            "user_id": user_id,
            "exp": expires,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            log.info("refresh_token_created", user_id=user_id)
            return token
        except Exception as e:
            log.error("refresh_token_creation_failed", error=str(e))
            raise
    
    def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verify token type
            if payload.get("type") != "access":
                raise JWTError("Invalid token type")
            
            user_id = payload.get("user_id")
            email = payload.get("email")
            username = payload.get("username")
            is_admin = payload.get("is_admin", False)
            
            if not all([user_id, email, username]):
                raise JWTError("Missing required fields in token")
            
            return TokenData(
                user_id=user_id,
                email=email,
                username=username,
                is_admin=is_admin
            )
        except JWTError as e:
            log.error("token_verification_failed", error=str(e))
            raise
    
    def verify_refresh_token(self, token: str) -> str:
        """Verify refresh token and return user_id"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != "refresh":
                raise JWTError("Invalid refresh token type")
            
            user_id = payload.get("user_id")
            if not user_id:
                raise JWTError("Missing user_id in refresh token")
            
            return user_id
        except JWTError as e:
            log.error("refresh_token_verification_failed", error=str(e))
            raise


# ---- Global JWT handler ----

def get_jwt_handler(secret_key: str, algorithm: str = "HS256", expiry_minutes: int = 1440) -> JWTHandler:
    """Factory function to create JWT handler"""
    return JWTHandler(secret_key, algorithm, expiry_minutes)
