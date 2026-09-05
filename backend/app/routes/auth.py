import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database import get_db
from app.schemas import (
    UserCreate,
    UserLogin,
    TokenResponse,
    UserResponse,
    APIResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.models import User, PasswordResetToken
from app.dependencies import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    pwd_context,
    is_admin_user,
    validate_password_strength,
)
from app.config import settings
from app.services.password_reset_service import (
    generate_reset_token,
    hash_token,
    is_throttled,
    record_request,
)
from app.services.email_service import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ─────────────────────────────────────────────────────────────────────────────
# Failed-login throttle (§7) — per email+IP, in-memory (mirrors the rate-limiter
# fallback; swap for Redis in a multi-instance deploy). Locks an attacker out of
# a single account after repeated misses without punishing other users sharing
# the IP. The generic request limiter still bounds overall traffic.
# ─────────────────────────────────────────────────────────────────────────────
_login_failures: dict[str, deque] = defaultdict(deque)
LOGIN_THROTTLE_WINDOW_SECONDS = 15 * 60   # 15 minutes
LOGIN_THROTTLE_MAX_ATTEMPTS = 10          # failed tries before a temporary lock


def _login_key(email: str, request: Request | None) -> str:
    ip = request.client.host if request and request.client else "unknown"
    return f"{email}|{ip}"


def _login_is_throttled(email: str, request: Request | None) -> bool:
    window = _login_failures[_login_key(email, request)]
    now = time.time()
    while window and window[0] < now - LOGIN_THROTTLE_WINDOW_SECONDS:
        window.popleft()
    return len(window) >= LOGIN_THROTTLE_MAX_ATTEMPTS


def _login_record_failure(email: str, request: Request | None) -> None:
    _login_failures[_login_key(email, request)].append(time.time())


def _login_clear_failures(email: str, request: Request | None) -> None:
    _login_failures.pop(_login_key(email, request), None)

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
    # Normalize credentials (defense-in-depth; the web client also trims).
    # Lowercasing the email prevents duplicate accounts via case variations.
    # The password is NOT stripped — leading/trailing spaces are a valid part of
    # a passphrase, and silently altering it would be a login footgun.
    email = user_data.email.strip().lower()
    password = user_data.password

    ok, reason = validate_password_strength(password, email)
    if not ok:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=reason)

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
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Login and receive access token.
    
    Use username field for email and password for password.
    """
    # Normalize credentials to match signup normalization (email only; a
    # password is never stripped so padded passphrases stay byte-identical).
    email = form_data.username.strip().lower()
    password = form_data.password

    if _login_is_throttled(email, request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Wait a few minutes and try again.",
        )

    # Find user by email
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not verify_password(password, user.hashed_password):
        _login_record_failure(email, request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _login_clear_failures(email, request)

    # Create access token (carries `ver` so a later password reset revokes it).
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "ver": user.token_version or 0},
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

    `is_admin` is computed (flag OR admin email) so the client-side admin gate
    matches the server-side `require_admin`, which also honours ADMIN_EMAILS.
    """
    current_user.is_admin = is_admin_user(current_user)
    return current_user

@router.post("/logout")
async def logout():
    """
    Logout - client should discard the token.
    
    No server-side action needed for JWT-based auth.
    """
    return {"message": "Logged out successfully. Please discard your token."}


# ─────────────────────────────────────────────────────────────────────────────
# Password reset (forgot password) — anti-enumeration, single-use, expiring.
# ─────────────────────────────────────────────────────────────────────────────

GENERIC_FORGOT_MESSAGE = "If an account exists for that email, a reset link is on its way."


@router.post("/forgot-password")
async def forgot_password(
    req: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Request a password-reset link.

    Always returns 200 with identical body whether or not the email exists
    (anti-enumeration). A per-email throttle stops reset-link bombing.
    """
    email = req.email.strip().lower()

    if is_throttled(email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many reset requests. Please wait a few minutes.",
        )
    # Record for both known and unknown addresses so an attacker can't probe
    # existence by hammering guesses without ever being throttled.
    record_request(email)

    # Generate/hash the token in *both* branches so timing is roughly equal for
    # existing vs. non-existing accounts (mitigates a latency side-channel).
    raw = generate_reset_token()
    hashed = hash_token(raw)

    user = db.query(User).filter(User.email == email).first()
    if user is not None:
        # One outstanding token per user: invalidate any previous unused tokens.
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).delete(synchronize_session=False)

        expires_at = datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)
        db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=hashed,
            expires_at=expires_at,
        ))
        db.commit()

        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={raw}"
        send_password_reset_email(email, reset_url)

    return {"message": GENERIC_FORGOT_MESSAGE}


@router.get("/reset-password/verify")
async def verify_reset_token(
    token: str = Query(..., min_length=20, max_length=512),
    db: Session = Depends(get_db),
):
    """Check whether a reset token is still valid (used by the reset page)."""
    hashed = hash_token(token.strip())
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == hashed
    ).first()
    if _token_is_invalid(reset):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired.",
        )
    return {"valid": True}


@router.post("/reset-password")
async def reset_password(
    req: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Set a new password using a valid, single-use reset token.

    Marks the token as used, removes any other outstanding tokens, and bumps the
    user's ``token_version`` so all previously issued access tokens are revoked.
    """
    hashed = hash_token(req.token.strip())
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == hashed
    ).first()

    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="This reset link is invalid or has expired.",
    )
    if _token_is_invalid(reset):
        raise invalid

    user = db.query(User).filter(User.id == reset.user_id).first()
    if user is None:
        raise invalid

    ok, reason = validate_password_strength(req.new_password, user.email)
    if not ok:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=reason)

    user.hashed_password = get_password_hash(req.new_password)
    user.token_version = (user.token_version or 0) + 1  # revoke existing sessions

    reset.used_at = datetime.utcnow()
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != reset.id,
    ).delete(synchronize_session=False)
    db.commit()

    return {"message": "Password updated. You can now log in with your new password."}


def _token_is_invalid(reset) -> bool:
    """True when a reset token is missing, already used, or expired."""
    if reset is None or reset.used_at is not None:
        return True
    if reset.expires_at is not None and reset.expires_at < datetime.utcnow():
        return True
    return False