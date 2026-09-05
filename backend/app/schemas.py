from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# ──────────────────────────────────────────────────────────────────
# Auth schemas
# ──────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=512)
    new_password: str = Field(..., min_length=8, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str

# ──────────────────────────────────────────────────────────────────
# Profile schemas
# ──────────────────────────────────────────────────────────────────
class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    age: Optional[int] = None
    gender: Optional[str] = None
    goals: Optional[list] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    skin_type: Optional[str] = None
    skin_concerns: Optional[list] = None
    commitment: Optional[str] = None
    onboarding_completed: bool
    subscription_tier: str
    is_subscribed: bool
    is_admin: bool
    total_checkins: int
    current_streak: int
    longest_streak: int
    current_day: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=13, le=120)
    gender: Optional[str] = None  # "male", "female", "other"
    goals: Optional[List[str]] = None  # ["improve_skin", "jawline", "confidence"]
    height: Optional[int] = Field(None, ge=100, le=250)  # cm
    weight: Optional[int] = Field(None, ge=30, le=300)  # kg
    location: Optional[str] = None
    bio: Optional[str] = None
    skin_type: Optional[str] = None  # oily | dry | combination | normal | sensitive
    skin_concerns: Optional[List[str]] = None  # ["acne", "dark_spots", ...]
    commitment: Optional[str] = None  # casual | consistent | locked_in

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────
# Photo schemas
# ──────────────────────────────────────────────────────────────────
class PhotoUploadResponse(BaseModel):
    id: str
    user_id: str
    file_url: str
    score: Optional[float]
    is_baseline: bool
    week_number: Optional[int] = None
    captured_at: datetime
    analysis_status: Optional[str] = None
    debug_timings: Optional[dict] = None

    class Config:
        from_attributes = True

class PhotoStatusResponse(BaseModel):
    id: str
    analysis_status: str  # pending | processing | completed | failed
    score: Optional[float] = None
    potential_score: Optional[float] = None
    raw_score: Optional[float] = None
    model_used: Optional[bool] = None
    improvement_potential: Optional[str] = None
    category_breakdown: Optional[dict] = None
    strengths: Optional[list] = None
    weaknesses: Optional[list] = None
    error: Optional[str] = None
    message: Optional[str] = None

    class Config:
        from_attributes = True

class PhotoAnalysisResponse(BaseModel):
    score: float
    potential_score: Optional[float] = None
    symmetry_score: Optional[float]
    skin_score: Optional[float]
    jawline_score: Optional[float]
    eye_score: Optional[float]
    nose_score: Optional[float]
    strengths: List[str]
    weaknesses: List[str]
    analysis_details: dict

# ──────────────────────────────────────────────────────────────────
# Plan schemas
# ──────────────────────────────────────────────────────────────────
class PlanResponse(BaseModel):
    id: str
    total_days: int
    current_day: int
    daily_tasks: Optional[dict]
    is_active: bool
    created_at: datetime

class CheckinRequest(BaseModel):
    week_number: int
    completed_tasks: List[str]

class CheckinLogRequest(BaseModel):
    completed_tasks: Optional[List[str]] = None
    notes: Optional[str] = None


# ──────────────────────────────────────────────────────────────────
# Progress schemas
# ──────────────────────────────────────────────────────────────────
class CheckinRecord(BaseModel):
    id: str
    user_id: str
    week_number: int
    progress_score: Optional[float] = None
    notes: Optional[str] = None
    completed_tasks: Optional[list] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────
# Response wrapper
# ──────────────────────────────────────────────────────────────────
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


# ──────────────────────────────────────────────────────────────────
# Admin product schemas
# ──────────────────────────────────────────────────────────────────
class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    brand: Optional[str] = None
    category: str = Field(..., max_length=50)
    price: float = Field(0.0, ge=0)
    currency: str = Field("USD", max_length=10)
    tier: str = Field("mid_range", max_length=20)
    image_url: Optional[str] = None
    affiliate_url: Optional[str] = None
    description: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    review_count: int = Field(0, ge=0)
    tags: Optional[List[str]] = None
    recommended_for: Optional[List[str]] = None
    social_proof: Optional[str] = None
    commission: Optional[float] = Field(None, ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    brand: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    tier: Optional[str] = Field(None, max_length=20)
    image_url: Optional[str] = None
    affiliate_url: Optional[str] = None
class OnboardingUpdate(BaseModel):
    """Everything the onboarding wizard may save in one call (§8.4)."""
    age: Optional[int] = Field(None, ge=13, le=120)
    gender: Optional[str] = None
    goals: Optional[List[str]] = None
    skin_type: Optional[str] = None
    skin_concerns: Optional[List[str]] = None
    height: Optional[int] = Field(None, ge=100, le=250)
    weight: Optional[int] = Field(None, ge=30, le=300)
    commitment: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None

    class Config:
        from_attributes = True


class CheckoutIn(BaseModel):
    tier: str = Field(..., pattern="^(pro|elite)$")
    annual: bool = True


class TestUpgradeIn(BaseModel):
    tier: str = Field(..., pattern="^(pro|elite)$")

    description: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    review_count: Optional[int] = Field(None, ge=0)
    tags: Optional[List[str]] = None
    recommended_for: Optional[List[str]] = None
    social_proof: Optional[str] = None
    commission: Optional[float] = Field(None, ge=0)