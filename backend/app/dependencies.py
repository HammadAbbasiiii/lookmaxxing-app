from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import SessionLocal, get_db
from app.config import settings
from jose import jwt, JWTError
from datetime import datetime, timedelta
from passlib.context import CryptContext

from app.models import User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_db_session():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password for storage"""
    return pwd_context.hash(password)


# ─────────────────────────────────────────────────────────────────────────────
# Password strength (§7, §13) — a real minimum bar, not just a length check.
# Rejects the top handful of trivially-guessable passwords and requires a mix of
# at least two character classes (lower / upper / digit / symbol). The frontend
# mirrors these rules in its live strength meter so messages never disagree.
# ─────────────────────────────────────────────────────────────────────────────

COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789", "1234567890",
    "qwerty", "qwerty123", "qwertyuiop", "letmein", "lookmaxx", "lookmaxxing",
    "iloveyou", "admin123", "welcome1", "monkey123", "football", "baseball",
    "dragon123", "sunshine", "princess", "trustno1", "abc123", "11111111",
    "00000000", "aaaaaaaa", "changeme", "master123", "superman1", "batman123",
}


def validate_password_strength(password: str, email: str | None = None) -> tuple[bool, str]:
    """Return ``(ok, error_message)`` for a candidate password.

    Length bounds are enforced by the Pydantic schema (min 8 / max 128); this
    function adds the human checks Pydantic can't express: blacklisted/common
    passwords, email-adjacent passwords, and the two-class mix requirement.
    """
    lowered = password.lower()

    if lowered in COMMON_PASSWORDS:
        return False, "That password is too common. Choose something more unique."

    if email:
        clean_email = email.strip().lower()
        local = clean_email.split("@")[0]
        if lowered == clean_email or (len(local) >= 4 and local in lowered):
            return False, "Password can't be your email address."

    classes = 0
    if any(c.islower() for c in password):
        classes += 1
    if any(c.isupper() for c in password):
        classes += 1
    if any(c.isdigit() for c in password):
        classes += 1
    if any(not c.isalnum() for c in password):
        classes += 1

    if classes < 2:
        return False, "Password must use at least two of: lowercase, uppercase, numbers, or symbols."

    return True, ""

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    # Session revocation: if the token carries a version it must match the user's
    # current token_version (bumped on password reset) — old sessions are rejected.
    if "ver" in payload and payload.get("ver") != (user.token_version or 0):
        raise credentials_exception
    return user


# Optional auth — returns None when the token is missing/invalid (used by /track).
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user_optional(
    token: str = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
):
    """Like get_current_user, but never raises 401 — returns None if anonymous."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
    except JWTError:
        return None

    return db.query(User).filter(User.id == user_id).first()


def is_admin_user(user: User) -> bool:
    """True when the user has the is_admin flag OR their email is in ADMIN_EMAILS."""
    if getattr(user, "is_admin", False):
        return True
    admin_emails = getattr(settings, "ADMIN_EMAILS", []) or []
    return bool(user.email) and user.email.lower() in admin_emails


def require_admin(user: User = Depends(get_current_user)):
    """Gate /admin/* — requires the is_admin flag OR an email in ADMIN_EMAILS."""
    if not is_admin_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# ─────────────────────────────────────────────────────────────────────────────
# Premium tier gating (§5.2 — server-authoritative; the browser is untrusted).
#
# Each gated endpoint calls one of these independently. The 403 `detail` is a
# dict carrying a machine-readable `code` so the client can tell an "upgrade
# required" 403 from any other 403.
# ─────────────────────────────────────────────────────────────────────────────

VALID_TIERS = ("free", "pro", "elite")


def is_premium(user: User) -> bool:
    """True when the user is on a paid tier (pro or elite)."""
    return (user.subscription_tier or "free").lower() in ("pro", "elite")


def require_pro(user: User = Depends(get_current_user)):
    """Gate premium endpoints — requires pro or elite."""
    if not is_premium(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "upgrade_required",
                "message": "Upgrade to Pro to unlock this feature.",
            },
        )
    return user


def require_elite(user: User = Depends(get_current_user)):
    """Gate elite-only endpoints."""
    if (user.subscription_tier or "free").lower() != "elite":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "upgrade_required",
                "message": "Upgrade to Elite to unlock this feature.",
            },
        )
    return user