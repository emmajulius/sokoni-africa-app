from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from config import settings
from database import get_db
from models import User, UserType

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    try:
        # Use bcrypt directly to avoid passlib initialization issues
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        # Fallback to passlib if bcrypt fails
        return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt directly"""
    # Bcrypt has a 72-byte limit, so we need to truncate if necessary
    # Encode to bytes and truncate to 72 bytes if needed
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Use bcrypt directly to avoid passlib initialization issues
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode JWT access token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print(f"ERROR: Token expired")
        return None
    except jwt.JWTError as e:
        print(f"ERROR: JWT decode error: {e}")
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error decoding token: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    print(f"\n{'='*60}")
    print(f"AUTHENTICATION CHECK")
    print(f"{'='*60}")
    print(f"Token received: {token[:30]}...")
    print(f"SECRET_KEY length: {len(settings.SECRET_KEY)}")
    
    payload = decode_access_token(token)
    
    if payload is None:
        print(f"ERROR: Failed to decode token")
        print(f"{'='*60}\n")
        raise credentials_exception
    
    print(f"Token decoded successfully")
    print(f"Payload: {payload}")
    
    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        print(f"ERROR: No 'sub' in payload")
        print(f"{'='*60}\n")
        raise credentials_exception
    
    # Handle case where sub might be a string (from older tokens) or int (from newer tokens)
    if isinstance(user_id_raw, str):
        try:
            user_id = int(user_id_raw)
        except (ValueError, TypeError):
            print(f"ERROR: Invalid user ID format in token: {user_id_raw}")
            print(f"{'='*60}\n")
            raise credentials_exception
    elif isinstance(user_id_raw, int):
        user_id = user_id_raw
    else:
        print(f"ERROR: Invalid user ID type in token: {type(user_id_raw)}")
        print(f"{'='*60}\n")
        raise credentials_exception
    
    print(f"User ID from token: {user_id}")
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        print(f"ERROR: User with ID {user_id} not found in database")
        print(f"{'='*60}\n")
        raise credentials_exception
    
    print(f"User found: {user.username} (ID: {user.id})")
    print(f"User active: {user.is_active}")
    print(f"User type: {user.user_type}")
    print(f"{'='*60}\n")
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (non-guest)"""
    if current_user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest users cannot perform this action"
        )
    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None (for optional auth endpoints)"""
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        
        if payload is None:
            return None
        
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            return None
        
        # Handle case where sub might be a string or int
        if isinstance(user_id_raw, str):
            try:
                user_id = int(user_id_raw)
            except (ValueError, TypeError):
                return None
        elif isinstance(user_id_raw, int):
            user_id = user_id_raw
        else:
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            return None
        
        return user
    except Exception:
        return None


def require_user_type(*allowed_types: UserType):
    """Dependency to require specific user types"""
    def check_user_type(current_user: User = Depends(get_current_active_user)):
        if current_user.user_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required user types: {', '.join([t.value for t in allowed_types])}"
            )
        return current_user
    return check_user_type

