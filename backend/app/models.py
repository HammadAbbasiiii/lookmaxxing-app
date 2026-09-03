from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Boolean, Text, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    
    # Profile
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)  # "male", "female", "other"
    goals = Column(JSON, nullable=True)  # ["improve_skin", "jawline", "confidence"]
    height = Column(Integer, nullable=True)  # cm
    weight = Column(Integer, nullable=True)  # kg
    location = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Onboarding
    onboarding_completed = Column(Boolean, default=False)

    # Admin (flag OR email listed in ADMIN_EMAILS env)
    is_admin = Column(Boolean, default=False)
    
    # Subscription
    is_subscribed = Column(Boolean, default=False)
    subscription_tier = Column(String(50), default="free")
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)
    subscription_customer_id = Column(String(255), nullable=True)
    
    # Progress & streak
    plan_start_date = Column(DateTime, nullable=True)
    current_day = Column(Integer, default=0)
    target_score = Column(Integer, nullable=True)
    total_checkins = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_checkin_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    photos = relationship("Photo", back_populates="user", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="user", cascade="all, delete-orphan")

class Photo(Base):
    __tablename__ = "photos"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Image metadata
    file_url = Column(String(500), nullable=False)  # Cloudinary/S3 URL
    file_size = Column(Integer, nullable=True)  # Bytes
    file_type = Column(String(50), nullable=True)  # jpg/png/heic
    
    # Analysis results
    score = Column(Float, nullable=True)  # Overall 0-100
    symmetry_score = Column(Float, nullable=True)
    skin_score = Column(Float, nullable=True)
    jawline_score = Column(Float, nullable=True)
    eye_score = Column(Float, nullable=True)
    nose_score = Column(Float, nullable=True)
    face_shape = Column(String(50), nullable=True)  # Round/Oval/Square/Heart
    
    # Detailed analysis (JSON)
    analysis_details = Column(JSON, nullable=True)  # Full DeepSeek analysis
    strengths = Column(JSON, nullable=True)  # Array of strengths
    weaknesses = Column(JSON, nullable=True)  # Array of weaknesses
    
    # Analysis status
    analysis_status = Column(String(20), default="pending")  # pending | processing | completed | failed

    # Tracking
    is_baseline = Column(Boolean, default=False)  # First photo = baseline
    week_number = Column(Integer, default=1)  # Which week of the plan
    captured_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="photos")
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_photo_user_captured", "user_id", "captured_at"),
        Index("idx_photo_user_baseline", "user_id", "is_baseline"),
    )

class Plan(Base):
    __tablename__ = "plans"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    photo_id = Column(String, ForeignKey("photos.id"), nullable=True)  # Link to analyzed photo
    
    # Plan details
    total_days = Column(Integer, default=90)
    current_day = Column(Integer, default=0)
    current_phase = Column(String(50), default="week_1")
    current_week = Column(Integer, default=1)
    
    # Structurd data (full plan JSON from AI)
    data = Column(JSON, nullable=True)
    phases = Column(JSON, nullable=True)
    
    # Daily tasks (JSON array)
    daily_tasks = Column(JSON, nullable=True)  # [{day:1, tasks:[...], completed:false}]
    
    # Progress milestones
    milestones = Column(JSON, nullable=True)  # [{day:30, achieved:false}, {day:60, achieved:false}]
    
    # Product recommendations (affiliate links)
    recommended_products = Column(JSON, nullable=True)  # [{name, link, price, commission}]
    
    # Status
    is_active = Column(Boolean, default=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="plans")
    photo = relationship("Photo", backref="plan")
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_plan_user_active", "user_id", "is_active"),
    )

class UserCheckin(Base):
    __tablename__ = "user_checkins"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    week_number = Column(Integer, nullable=False)
    photo_id = Column(String, ForeignKey("photos.id"), nullable=True)  # Check-in photo
    progress_score = Column(Float, nullable=True)  # New score
    notes = Column(Text, nullable=True)  # User's own notes
    completed_tasks = Column(JSON, nullable=True)  # Which tasks were done
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Indexes for common queries


class AnalyticsEvent(Base):
    """Privacy-first event log (§17) — page views, session timing, CTA clicks.

    Carries NO faces, NO emails, NO tokens. user_id is nullable so anonymous
    landing visitors are still counted for top-of-funnel measurement.
    """

    __tablename__ = "analytics_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String(64), nullable=True, index=True)
    event_name = Column(String(64), nullable=False, index=True)
    page = Column(String(255), nullable=True)
    referrer = Column(String(255), nullable=True)
    # Named `properties` (not `metadata`) — `metadata` is reserved in the
    # SQLAlchemy Declarative API (every mapped class already has `.metadata`).
    properties = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_event_name_created", "event_name", "created_at"),
        Index("idx_event_user_created", "user_id", "created_at"),
    )
