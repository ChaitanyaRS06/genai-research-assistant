from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import UserCreate, UserLogin, Token, UserResponse, authenticate_user, create_user, get_current_user
from app.utils.security import create_access_token

# Create router for user-related endpoints
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/signup", response_model=Token)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.
    
    - **email**: Valid email address (must be unique)
    - **password**: User password (will be hashed)
    - **full_name**: Optional user's full name
    
    Returns JWT token for immediate login.
    """
    try:
        # Create user (this will raise HTTPException if email exists)
        user = create_user(db, user_data)
        
        # Create access token for the new user
        access_token = create_access_token(data={"sub": user.email})
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions (like email already exists)
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns JWT token for accessing protected endpoints.
    """
    # Authenticate user
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Get current user's profile information.
    
    Requires valid JWT token in Authorization header:
    Authorization: Bearer <your_jwt_token>
    """
    return current_user

@router.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    """
    Example protected route that requires authentication.
    
    This demonstrates how to protect any endpoint by adding the
    current_user dependency.
    """
    return {
        "message": f"Hello {current_user.email}! This is a protected route.",
        "user_id": current_user.id
    }