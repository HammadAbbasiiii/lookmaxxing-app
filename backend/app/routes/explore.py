"""
Explore Routes — social proof (transformations) + education (articles).

Endpoints:
- GET /explore → {"transformations": [...], "articles": [...]}

Transformations are derived from real user progress: users with at least two
scored photos whose score improved between their earliest and latest photo.
Usernames are anonymised to a stable, deterministic pseudonym (e.g. "Brave
Falcon") with avatar initials and a celebratory rank label, so no real identity
is ever exposed.

Articles are curated, evergreen seed content covering looksmaxxing / grooming /
skincare topics. Replace `ARTICLES` with your own blog or CMS content when ready.
"""

import hashlib

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Photo, User

router = APIRouter(prefix="/explore", tags=["Explore"])

# Curated seed articles. `image_url` may be None (the client renders text-only).
ARTICLES = [
    {
        "id": "art_skincare_routine",
        "title": "Build a Skincare Routine That Actually Works",
        "summary": "The science-backed order of cleanser, moisturiser and SPF — and why consistency beats complexity.",
        "url": "https://en.wikipedia.org/wiki/Skin_care",
        "image_url": None,
    },
    {
        "id": "art_facial_symmetry",
        "title": "Facial Symmetry: What Makes a Face Attractive",
        "summary": "Why symmetry signals health, and how small daily habits can improve your proportions over time.",
        "url": "https://en.wikipedia.org/wiki/Facial_symmetry",
        "image_url": None,
    },
    {
        "id": "art_mewing",
        "title": "Mewing & Tongue Posture, Explained",
        "summary": "What orthotropics says about resting tongue posture and jawline definition.",
        "url": "https://en.wikipedia.org/wiki/Mewing",
        "image_url": None,
    },
    {
        "id": "art_sleep",
        "title": "How Sleep Shapes Your Skin & Jawline",
        "summary": "Recovery is where progress happens — here's why 7–9 hours matters for your face.",
        "url": "https://en.wikipedia.org/wiki/Sleep",
        "image_url": None,
    },
    {
        "id": "art_grooming",
        "title": "Beard & Grooming: Framing Your Jawline",
        "summary": "How the right grooming frames your strongest features and softens the rest.",
        "url": "https://en.wikipedia.org/wiki/Beard",
        "image_url": None,
    },
    {
        "id": "art_diet",
        "title": "Diet, Hydration & Skin Health",
        "summary": "What you eat shows up on your face — the nutrients that drive clear, firm skin.",
        "url": "https://en.wikipedia.org/wiki/Diet_(nutrition)",
        "image_url": None,
    },
]


_ADJECTIVES = [
    "Brave", "Golden", "Rising", "Sharp", "Bold", "Calm", "Swift", "Bright",
    "Noble", "Fearless", "Loyal", "Steady", "Keen", "Fierce", "Wise", "Proud",
]
_NOUNS = [
    "Falcon", "Tiger", "Wolf", "Hawk", "Lion", "Phoenix", "Panther", "Eagle",
    "Otter", "Raven", "Fox", "Bear", "Lynx", "Cobra", "Jaguar", "Sable",
]


def _identity(user: User) -> dict:
    """Return a stable, privacy-safe display identity for a member.

    We never show a real name or a fake first name ("Alex", "Noah", …) — both
    confused members and weakened privacy. Instead every transformation gets a
    deterministic pseudonym ("Brave Falcon") plus its initials for the avatar,
    derived only from the user id.
    """
    digest = hashlib.md5(user.id.encode("utf-8")).hexdigest()
    adj = _ADJECTIVES[int(digest[:4], 16) % len(_ADJECTIVES)]
    noun = _NOUNS[int(digest[4:8], 16) % len(_NOUNS)]
    return {"username": f"{adj} {noun}", "initials": f"{adj[0]}{noun[0]}"}


def _rank_label(delta: float) -> str:
    """A celebratory (never shaming) label for a member's score improvement."""
    if delta >= 6:
        return "Glow-Up Legend"
    if delta >= 3:
        return "Rising Star"
    if delta >= 1.5:
        return "Most Improved"
    return "On the Rise"


@router.get("")
async def get_explore(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the Explore feed: real transformations (anonymised) + curated articles.
    """
    scored_photos = (
        db.query(Photo)
        .filter(Photo.score.isnot(None))
        .order_by(Photo.user_id, Photo.captured_at.asc())
        .all()
    )

    by_user = {}
    for photo in scored_photos:
        by_user.setdefault(photo.user_id, []).append(photo)

    transformations = []
    for user_id, photos in by_user.items():
        if user_id == current_user.id:
            continue
        if len(photos) < 2:
            continue

        baseline = photos[0]   # earliest scored photo
        latest = photos[-1]    # most recent scored photo
        before = baseline.score
        after = latest.score
        if before is None or after is None or after <= before:
            continue

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            continue

        identity = _identity(user)
        delta = after - before
        transformations.append(
            {
                "id": f"tx_{user_id}",
                "username": identity["username"],
                "initials": identity["initials"],
                "rank_label": _rank_label(delta),
                "before_score": round(before, 1),
                "after_score": round(after, 1),
                "before_image_url": baseline.file_url,
                "after_image_url": latest.file_url,
            }
        )

    # Most impressive improvements first, cap the feed length.
    transformations.sort(
        key=lambda t: t["after_score"] - t["before_score"], reverse=True
    )
    transformations = transformations[:12]

    return {
        "success": True,
        "transformations": transformations,
        "articles": ARTICLES,
        "total": len(transformations),
    }
