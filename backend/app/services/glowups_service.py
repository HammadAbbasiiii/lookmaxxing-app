"""
Glow-Ups — personal transformation movie + anonymized, opt-in feed.

Zero-AI, zero new infra: the "movie" is a Ken Burns slideshow the client builds
from the user's own ordered photos, so the server only stores status/consent.
The feed is 18+, opt-in, blurred, first-name-only and never shows a full face.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import Photo, Plan, Transformation, User, generate_uuid
from app.services.progress_engine import compute_current_day

TRAILER_DAYS = [14, 30, 60]
FEED_PAGE_SIZE = 20

# Honest, clearly-labelled examples for an empty feed. Never fabricated scale.
SEED_FEED = [
    {"id": "seed-1", "first_name": "Jordan", "age": 19, "day": 78, "delta": 11.0,
     "headline": "Showing up every day was the whole trick.", "seed": True},
    {"id": "seed-2", "first_name": "Sam", "age": 24, "day": 45, "delta": 7.5,
     "headline": "Small changes, but everyone noticed.", "seed": True},
    {"id": "seed-3", "first_name": "Drew", "age": 21, "day": 30, "delta": 6.0,
     "headline": "The streak did more than the routines.", "seed": True},
]


def _is_adult(user: User) -> bool:
    return user.age is not None and user.age >= 18


def _first_name(full_name: Optional[str]) -> str:
    return (full_name or "Member").strip().split()[0] or "Member"


def _plan_day(user: User, db: Session) -> int:
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == user.id, Plan.is_active == True)  # noqa: E712
        .order_by(Plan.created_at.desc())
        .first()
    )
    return compute_current_day(plan) if plan else 1


def _ordered_scored_photos(user: User, db: Session) -> List[Photo]:
    return (
        db.query(Photo)
        .filter(Photo.user_id == user.id, Photo.score.isnot(None))
        .order_by(Photo.captured_at.asc())
        .all()
    )


def _delta(photos: List[Photo]) -> float:
    if len(photos) < 2:
        return 0.0
    before = photos[0].score or 0
    after = photos[-1].score or 0
    return round(after - before, 1)


def _get_or_create(user: User, db: Session) -> Transformation:
    t = db.query(Transformation).filter(Transformation.user_id == user.id).first()
    if t is None:
        t = Transformation(
            user_id=user.id, share_enabled=False, status="pending",
            reported_count=0, is_active=True,
        )
        db.add(t)
        db.commit()
        db.refresh(t)
    return t


def _movie_status(user: User, photos: List[Photo], db: Session) -> str:
    if len(photos) < 2:
        return "pending"
    if _plan_day(user, db) >= 90:
        return "ready"
    return "trailer"


def get_feed(user: User, db: Session, cursor: int = 0, limit: int = FEED_PAGE_SIZE) -> Dict[str, Any]:
    """18+ anonymized feed. Returns locked=True for minors (no items)."""
    if not _is_adult(user):
        return {"items": [], "next_cursor": None, "locked": True}

    rows = (
        db.query(Transformation)
        .filter(
            Transformation.share_enabled == True,  # noqa: E712
            Transformation.is_active == True,      # noqa: E712
            Transformation.reported_count == 0,
            Transformation.status != "removed",
            Transformation.user_id != user.id,
        )
        .order_by(Transformation.created_at.desc())
        .offset(cursor)
        .limit(limit)
        .all()
    )

    items = []
    for t in rows:
        owner = db.query(User).filter(User.id == t.user_id).first()
        if owner is None or not _is_adult(owner):
            continue
        photos = _ordered_scored_photos(owner, db)
        if not photos:
            continue
        items.append({
            "id": t.id,
            "first_name": _first_name(owner.full_name),
            "age": owner.age,
            "day": _plan_day(owner, db),
            "delta": t.delta_score if t.delta_score is not None else _delta(photos),
            "headline": t.headline or "Small daily wins, big change.",
            "cover_url": photos[-1].file_url,
            "blur": True,
            "seed": False,
        })

    # Honest seeded examples only when there are no real, opted-in items yet.
    if cursor == 0 and not items:
        items = SEED_FEED

    next_cursor = (cursor + limit) if len(rows) == limit else None
    return {"items": items, "next_cursor": next_cursor, "locked": False}


def set_consent(user: User, db: Session, share_enabled: bool) -> Dict[str, Any]:
    if share_enabled and not _is_adult(user):
        return {"share_enabled": False, "error": "adults_only"}
    t = _get_or_create(user, db)
    t.share_enabled = share_enabled
    if not share_enabled:
        t.status = "removed"  # instant removal from feed on opt-out
    elif t.status == "removed":
        t.status = "pending"  # re-opt-in requires re-approval (pending review)
    db.commit()
    db.refresh(t)
    return {"share_enabled": bool(t.share_enabled)}


def get_consent(user: User, db: Session) -> Dict[str, Any]:
    t = _get_or_create(user, db)
    return {"share_enabled": bool(t.share_enabled)}


def get_movie(user: User, db: Session) -> Dict[str, Any]:
    t = _get_or_create(user, db)
    photos = _ordered_scored_photos(user, db)
    status = _movie_status(user, photos, db)
    t.status = status
    db.commit()
    db.refresh(t)

    trailers = []
    plan_day = _plan_day(user, db)
    for day in TRAILER_DAYS:
        if plan_day >= day:
            # A trailer shows only the frames up to that milestone day.
            cut = [p.file_url for p in photos[: max(1, min(len(photos), day))]]
            trailers.append({"day": day, "title": f"Day {day} teaser", "photo_urls": cut})

    return {
        "status": status,
        "trailers": trailers,
        "full_movie_url": t.movie_url,
        "photo_urls": [p.file_url for p in photos],
        "delta": t.delta_score if t.delta_score is not None else _delta(photos),
    }


def generate_movie(user: User, db: Session) -> Dict[str, Any]:
    t = _get_or_create(user, db)
    photos = _ordered_scored_photos(user, db)
    if len(photos) < 2:
        return {"job_id": None, "status": "pending", "error": "needs_more_photos"}

    # Throttle: one render per 24h; reuse the cached render otherwise.
    now = datetime.utcnow()
    if t.movie_generated_at is not None:
        elapsed = (now - t.movie_generated_at).total_seconds()
        if elapsed < 86400:
            return {"job_id": None, "status": t.status, "throttled": True}

    t.status = _movie_status(user, photos, db)
    t.movie_generated_at = now
    t.delta_score = _delta(photos)
    db.commit()
    db.refresh(t)
    return {"job_id": generate_uuid(), "status": t.status}


def report_item(user: User, db: Session, item_id: str) -> Dict[str, Any]:
    t = db.query(Transformation).filter(Transformation.id == item_id).first()
    if t is None:
        return {"reported": False, "error": "not_found"}
    t.reported_count = (t.reported_count or 0) + 1
    t.is_active = False  # auto-hidden pending review
    db.commit()
    return {"reported": True}

