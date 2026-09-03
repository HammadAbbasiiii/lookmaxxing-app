from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.schemas import UserCreate, UserLogin, TokenResponse, UserResponse, APIResponse
from app.models import User
from app.dependencies import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    pwd_context
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=UserResponse)
async def signup(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user account.
    
    - **email**: Valid email address
    - **password**: Minimum 6 characters
    - **full_name**: Optional display name
    """
    # Normalize credentials (defense-in-depth; the iOS client also trims).
    # Lowercasing the email prevents duplicate accounts via case variations.
    email = user_data.email.strip().lower()
    password = user_data.password.strip()

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=user_data.full_name,
        is_subscribed=False,
        subscription_tier="free",
        current_day=0
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login and receive access token.
    
    Use username field for email and password for password.
    """
    # Normalize credentials to match signup normalization.
    email = form_data.username.strip().lower()
    password = form_data.password.strip()

    # Find user by email
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile.
    
    Requires valid JWT token in Authorization header.
    """
    return current_user

@router.post("/logout")
async def logout():
    """
    Logout - client should discard the token.
    
    No server-side action needed for JWT-based auth.
    """
    return {"message": "Logged out successfully. Please discard your token."}