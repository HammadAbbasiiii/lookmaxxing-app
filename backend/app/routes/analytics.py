"""
Self-hosted, privacy-first analytics + admin overview (PRODUCT_SPEC §17).

Events carry NO faces, NO emails, NO tokens. The /track endpoint accepts an
optional bearer token purely to attribute events to a user_id; it never fails
loudly so the client can fire-and-forget.

Admin endpoints (/admin/*) are gated by `require_admin` (is_admin flag OR an
email listed in ADMIN_EMAILS env). They expose the data the operator needs to
understand engagement — user list, plans, check-ins, page views, time spent,
and the visit→signup→upload→upgrade funnel.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_optional, require_admin
from app.models import AnalyticsEvent, Photo, Plan, User, UserCheckin

router = APIRouter(tags=["Analytics"])


# ─────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────
class TrackEventIn(BaseModel):
    event_name: str = Field(..., max_length=64)
    page: Optional[str] = Field(default=None, max_length=255)
    referrer: Optional[str] = Field(default=None, max_length=255)
    session_id: Optional[str] = Field(default=None, max_length=64)
    metadata: Optional[Dict[str, Any]] = None


class TrackRequest(BaseModel):
    events: List[TrackEventIn]


# ─────────────────────────────────────────────────────────────────────
# POST /track — fire-and-forget event ingestion (auth optional)
# ─────────────────────────────────────────────────────────────────────
@router.post("/track")
async def track_events(
    payload: TrackRequest,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Log one or more events. Never blocks the client, never fails loudly."""
    events = payload.events[:50]
    if not events:
        return {"success": True, "logged": 0}
    try:
        for e in events:
            db.add(
                AnalyticsEvent(
                    user_id=user.id if user else None,
                    session_id=(e.session_id or "")[:64] or None,
                    event_name=e.event_name[:64],
                    page=e.page,
                    referrer=e.referrer,
                    metadata=e.metadata,
                )
            )
        db.commit()
        return {"success": True, "logged": len(events)}
    except Exception:
        db.rollback()
        return {"success": False, "logged": 0}


# ─────────────────────────────────────────────────────────────────────
# Admin: high-level overview (users, engagement, monetization, traffic)
# ─────────────────────────────────────────────────────────────────────
@router.get("/admin/overview")
async def admin_overview(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    day = now - timedelta(days=1)
    week = now - timedelta(days=7)
    month = now - timedelta(days=30)

    def _since(model, cutoff):
        return db.query(func.count(model.id)).filter(model.created_at >= cutoff).scalar() or 0

    def _dau(cutoff):
        return (
            db.query(func.count(func.distinct(AnalyticsEvent.user_id)))
            .filter(AnalyticsEvent.created_at >= cutoff, AnalyticsEvent.user_id.isnot(None))
            .scalar()
            or 0
        )

    # Average page dwell time, computed in Python (DB-agnostic JSON handling).
    exits = (
        db.query(AnalyticsEvent.metadata)
        .filter(AnalyticsEvent.event_name == "page_exit")
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(1000)
        .all()
    )
    durations = [
        (m or {}).get("duration_ms")
        for m in exits
        if isinstance(m, dict) and isinstance((m or {}).get("duration_ms"), (int, float))
    ]
    avg_session_sec = round(sum(durations) / len(durations) / 1000, 1) if durations else None

    return {
        "success": True,
        "users": {
            "total": db.query(func.count(User.id)).scalar() or 0,
            "new_24h": _since(User, day),
            "new_7d": _since(User, week),
            "new_30d": _since(User, month),
        },
        "engagement": {
            "photos": db.query(func.count(Photo.id)).scalar() or 0,
            "checkins": db.query(func.count(UserCheckin.id)).scalar() or 0,
            "plans": db.query(func.count(Plan.id)).scalar() or 0,
        },
        "monetization": {
            "pro": db.query(func.count(User.id)).filter(User.subscription_tier == "pro").scalar() or 0,
            "elite": db.query(func.count(User.id)).filter(User.subscription_tier == "elite").scalar() or 0,
        },
        "traffic": {
            "total_events": db.query(func.count(AnalyticsEvent.id)).scalar() or 0,
            "sessions": db.query(func.count(func.distinct(AnalyticsEvent.session_id)))
            .filter(AnalyticsEvent.session_id.isnot(None))
            .scalar()
            or 0,
            "dau": _dau(day),
            "wau": _dau(week),
            "mau": _dau(month),
            "avg_session_sec": avg_session_sec,
        },
    }


# ─────────────────────────────────────────────────────────────────────
# Admin: user list (searchable, with engagement + last-seen)
# ─────────────────────────────────────────────────────────────────────
@router.get("/admin/users")
async def admin_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
):
    q = db.query(User)
    if search:
        q = q.filter(User.email.ilike(f"%{search}%"))
    total = q.count()
    users = q.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    rows = []
    for u in users:
        last_seen = (
            db.query(func.max(AnalyticsEvent.created_at))
            .filter(AnalyticsEvent.user_id == u.id)
            .scalar()
        )
        event_count = (
            db.query(func.count(AnalyticsEvent.id)).filter(AnalyticsEvent.user_id == u.id).scalar()
            or 0
        )
        rows.append(
            {
                "id": u.id,
                "email": u.email,
                "tier": u.subscription_tier,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "current_day": u.current_day,
                "current_streak": u.current_streak,
                "total_checkins": u.total_checkins,
                "event_count": event_count,
                "last_seen": last_seen.isoformat() if last_seen else None,
            }
        )
    return {"success": True, "total": total, "users": rows}


# ─────────────────────────────────────────────────────────────────────
# Admin: single-user deep dive (plans, check-ins, photos, movement)
# ─────────────────────────────────────────────────────────────────────
@router.get("/admin/users/{user_id}")
async def admin_user_detail(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    photos = db.query(Photo).filter(Photo.user_id == user_id).order_by(Photo.captured_at.desc()).all()
    checkins = (
        db.query(UserCheckin)
        .filter(UserCheckin.user_id == user_id)
        .order_by(UserCheckin.created_at.desc())
        .limit(100)
        .all()
    )
    plans = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.created_at.desc()).all()
    events = (
        db.query(AnalyticsEvent)
        .filter(AnalyticsEvent.user_id == user_id)
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(200)
        .all()
    )

    # Aggregate time spent + pages viewed (computed in Python, DB-agnostic).
    page_counts: Dict[str, int] = {}
    durations = []
    for ev in events:
        if ev.event_name == "page_view" and ev.page:
            page_counts[ev.page] = page_counts.get(ev.page, 0) + 1
        if ev.event_name == "page_exit" and isinstance(ev.metadata, dict):
            d = ev.metadata.get("duration_ms")
            if isinstance(d, (int, float)):
                durations.append(d)
    total_time_sec = round(sum(durations) / 1000, 1) if durations else 0

    return {
        "success": True,
        "user": {
            "id": u.id,
            "email": u.email,
            "tier": u.subscription_tier,
            "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "current_day": u.current_day,
            "current_streak": u.current_streak,
            "longest_streak": u.longest_streak,
            "total_checkins": u.total_checkins,
            "onboarding_completed": u.onboarding_completed,
        },
        "photos": [
            {
                "id": p.id,
                "score": p.score,
                "is_baseline": p.is_baseline,
                "captured_at": p.captured_at.isoformat() if p.captured_at else None,
            }
            for p in photos
        ],
        "plans": [
            {
                "id": p.id,
                "current_day": p.current_day,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in plans
        ],
        "checkins": [
            {
                "id": c.id,
                "week_number": c.week_number,
                "progress_score": c.progress_score,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in checkins
        ],
        "analytics": {
            "total_time_sec": total_time_sec,
            "pages": page_counts,
            "recent_events": [
                {
                    "event": e.event_name,
                    "page": e.page,
                    "at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events[:50]
            ],
        },
    }


# ─────────────────────────────────────────────────────────────────────
# Admin: aggregate event summary (top pages, event mix, daily activity)
# ─────────────────────────────────────────────────────────────────────
@router.get("/admin/events/summary")
async def admin_events_summary(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    page_rows = (
        db.query(AnalyticsEvent.page, func.count(AnalyticsEvent.id))
        .filter(AnalyticsEvent.event_name == "page_view", AnalyticsEvent.page.isnot(None))
        .group_by(AnalyticsEvent.page)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(20)
        .all()
    )
    event_rows = (
        db.query(AnalyticsEvent.event_name, func.count(AnalyticsEvent.id))
        .group_by(AnalyticsEvent.event_name)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(20)
        .all()
    )

    daily = []
    today = datetime.utcnow().date()
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        start = datetime(d.year, d.month, d.day)
        end = start + timedelta(days=1)
        cnt = (
            db.query(func.count(AnalyticsEvent.id))
            .filter(AnalyticsEvent.created_at >= start, AnalyticsEvent.created_at < end)
            .scalar()
            or 0
        )
        daily.append({"date": d.isoformat(), "events": cnt})

    return {
        "success": True,
        "top_pages": [{"page": p, "views": c} for p, c in page_rows],
        "events": [{"event": e, "count": c} for e, c in event_rows],
        "daily": daily,
    }
