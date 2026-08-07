from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# ──────────────────────────────────────────────────────────────────
# Auth schemas
# ──────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

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
    onboarding_completed: bool
    subscription_tier: str
    is_subscribed: bool
    total_checkins: int
    current_streak: int
    longest_streak: int
    current_day: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None  # "male", "female", "other"
    goals: Optional[List[str]] = None  # ["improve_skin", "jawline", "confidence"]
    height: Optional[int] = None  # cm
    weight: Optional[int] = None  # kg
    location: Optional[str] = None
    bio: Optional[str] = None

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

    class Config:
        from_attributes = True

class PhotoAnalysisResponse(BaseModel):
    score: float
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