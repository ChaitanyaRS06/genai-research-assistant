from datetime import timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models import User
from app.utils.security import verify_password, get_password_hash, create_access_token, verify_token

# Security scheme for extracting Bearer tokens
security = HTTPBearer()

# Pydantic schemas for request/response validation
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    
    class Config:
        from_attributes = True  # Allows SQLAlchemy model conversion

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate user with email and password.
    
    Args:
        db: Database session
        email: User email
        password: Plain text password
        
    Returns:
        User object if authentication successful, None otherwise
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
        
    return user

def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Create a new user with hashed password.
    
    Args:
        db: Database session
        user_data: User creation data
        
    Returns:
        Created user object
        
    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user with hashed password
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user.
    
    Args:
        credentials: Bearer token from request header
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token and extract email
    email = verify_token(credentials.credentials)
    if email is None:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency to ensure current user is an admin.
    
    Returns:
        Current user if they are admin
        
    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user