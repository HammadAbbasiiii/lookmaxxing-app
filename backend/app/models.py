from sqlalchemy import Column, Integer, String, DateTime, Date, Float, JSON, Boolean, Text, ForeignKey, Index, UniqueConstraint
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

    # Skin / lifestyle — collected in onboarding, editable in settings. These
    # feed the plan generator + coach so recommendations are genuinely targeted.
    skin_type = Column(String(20), nullable=True)  # oily | dry | combination | normal | sensitive
    skin_concerns = Column(JSON, nullable=True)    # ["acne", "dark_spots", "redness", "dullness", "fine_lines"]
    commitment = Column(String(20), nullable=True) # casual | consistent | locked_in

    # Onboarding
    onboarding_completed = Column(Boolean, default=False)

    # Admin (flag OR email listed in ADMIN_EMAILS env)
    is_admin = Column(Boolean, default=False)

    # Auth session version — bumped on password reset so every previously issued
    # access token is invalidated (see get_current_user in dependencies.py).
    token_version = Column(Integer, default=0, nullable=False)
    
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


class Product(Base):
    """Admin-managed product catalogue (affiliate recommendations).

    Previously products lived in a static JSON file; they now live in the DB so
    the owner can add / edit / archive / re-activate products from the admin UI
    with no code changes or redeploys. `is_active` soft-deletes keep history.
    """

    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    brand = Column(String(255), nullable=True)
    category = Column(String(50), nullable=False, index=True)
    price = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), default="USD")
    tier = Column(String(20), default="mid_range", index=True)  # budget | mid_range | premium
    image_url = Column(String(500), nullable=True)
    affiliate_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0)
    tags = Column(JSON, nullable=True)
    recommended_for = Column(JSON, nullable=True)
    social_proof = Column(String(500), nullable=True)
    commission = Column(Float, nullable=True)  # affiliate commission %/amount
    is_active = Column(Boolean, default=True, index=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    __table_args__ = (
        Index("idx_product_cat_active", "category", "is_active"),
        Index("idx_product_tier_active", "tier", "is_active"),
    )


class AdminAction(Base):
    """Audit log of every mutating admin action (who changed what, when)."""

    __tablename__ = "admin_actions"

    id = Column(String, primary_key=True, default=generate_uuid)
    admin_email = Column(String(255), nullable=False, index=True)
    action = Column(String(64), nullable=False)  # create | update | delete | activate | import
    entity_type = Column(String(64), nullable=False)  # product | user | ...
    entity_id = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), index=True)


class PasswordResetToken(Base):
    """Single-use, expiring password-reset token.

    Stores only a SHA-256 **hash** of the random token (never the raw token), so a
    DB leak reveals nothing usable. One outstanding token per user; successful use
    (or a new request) invalidates the previous one.
    """

    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())


# ── Momentum engine: Glow (daily variable-reward reveal) ───────────────────
class GlowState(Base):
    """Daily Glow open state + streak. One row per user.

    Reveal *quality* is day-based (never streak-based, so a missed day is
    gain-framed — "pick up where you left off"), while the streak jackpot
    (Day 7 / Day 30) is streak-based, mirroring the plan streaks.
    """

    __tablename__ = "glow_states"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    last_open_date = Column(Date, nullable=True)           # server UTC date of last open
    glow_streak = Column(Integer, default=0)               # consecutive daily opens
    longest_glow_streak = Column(Integer, default=0)
    opens_count = Column(Integer, default=0)               # total opens (first-open hook detection)
    consecutive_commons = Column(Integer, default=0)       # pity timer
    milestone_flags = Column(JSON, nullable=True)          # {"streak7_claimed": true, "day90_claimed": true}

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class GlowReveal(Base):
    """Audit log of every opened Glow reward (one per user per calendar day)."""

    __tablename__ = "glow_reveals"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    open_date = Column(Date, nullable=False, index=True)   # server UTC date (idempotency key)
    journey_day = Column(Integer, nullable=False)          # plan day 1..90 at open time
    rarity = Column(String(16), nullable=False)            # common|rare|epic|legendary
    reward_type = Column(String(32), nullable=False)       # micro_win|glimpse|unlock|gold_glow|full_reveal
    payload = Column(JSON, nullable=True)

    opened_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_glow_user_date", "user_id", "open_date"),
    )


# ── Momentum engine: The Arc (RPG XP / levels / quests / badges) ────────────
class ArcState(Base):
    __tablename__ = "arc_states"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    total_xp = Column(Integer, default=0)
    current_level = Column(Integer, default=1)             # derived from total_xp
    quest_date = Column(Date, nullable=True)               # server UTC date quests were generated for
    quests = Column(JSON, nullable=True)                   # [{"id","focus","task","xp","claimed"}]
    xp_events = Column(JSON, nullable=True)                # {event_key: xp} idempotency ledger

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class UserBadge(Base):
    __tablename__ = "user_badges"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    badge_key = Column(String(64), nullable=False)
    awarded_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "badge_key", name="uq_user_badge"),
    )


# ── Momentum engine: Glow-Ups (transformation movie + anonymized feed) ──────
class Transformation(Base):
    __tablename__ = "transformations"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_ids = Column(JSON, nullable=True)                # ordered baseline → latest
    share_enabled = Column(Boolean, default=False)         # opt-in only
    status = Column(String(32), default="pending")         # pending|trailer|ready|removed
    movie_url = Column(String(500), nullable=True)
    movie_generated_at = Column(DateTime, nullable=True)   # render throttle (1/day)
    delta_score = Column(Float, nullable=True)
    headline = Column(String(255), nullable=True)          # the user's own one-liner
    reported_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)  # soft-delete for moderation

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
