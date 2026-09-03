"""
Daily AI coach (Pro/Elite) — one personalized, encouraging tip per day.

The tip is derived from the user's latest score and weakest categories, with an
optional DeepSeek call (cached per user+date) for a genuinely personalized line.
If DeepSeek/Redis are unavailable, a deterministic template tip is returned so
the endpoint always answers quickly and never costs extra tokens.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import require_pro
from app.models import Photo, User
from app.services.score_labels import get_score_label

router = APIRouter(tags=["Coach"])

# ── optional Redis (lazy, mirroring rate_limit.py) ───────────────────────────
_redis = None
_redis_checked = False


def _get_redis():
    global _redis, _redis_checked
    if _redis_checked:
        return _redis
    _redis_checked = True
    try:
        import redis as _r
        _redis = _r.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        _redis.ping()
    except Exception:
        _redis = None
    return _redis


def _coach_cache_key(user_id: str, day: str) -> str:
    return f"coach:{user_id}:{day}"


def _fallback_tip(user: User, weakest: List[str], score: Optional[float]) -> Dict[str, Any]:
    focus = weakest[0].replace("_", " ").title() if weakest else "consistency"
    label = get_score_label(score if score is not None else 0)["label"]
    return {
        "message": (
            f"Today, give two focused minutes to {focus.lower()}. Small, repeated "
            f"actions are what actually move your score — not motivation."
        ),
        "focus": focus,
        "tasks": [
            "Do today's plan task (2 min)",
            "Drink water before your first screens",
            "Hold good posture for 5 minutes",
        ],
        "score_context": label,
        "source": "template",
    }


def _deepseek_tip(user: User, score: Optional[float], weakest: List[str]) -> Optional[Dict[str, Any]]:
    """Attempt a personalized DeepSeek tip. Returns None on any failure."""
    if not settings.DEEPSEEK_API_KEY:
        return None

    day = datetime.utcnow().date().isoformat()
    cache_key = _coach_cache_key(user.id, day)
    r = _get_redis()
    if r is not None:
        try:
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    focus = ", ".join(weakest) if weakest else "overall balance"
    prompt = (
        "You are a concise, warm appearance coach. Write ONE sentence of encouragement "
        "and ONE concrete 2-minute action for today. Respond with JSON only, keys: "
        "message (string), focus (string), tasks (array of 3 short strings).\n"
        f"User's score: {score if score is not None else 'unknown'}.\n"
        f"Weakest areas: {focus}.\n"
        f"Goal areas: {', '.join(user.goals) if user.goals else 'general improvement'}.\n"
        f"Skin type: {user.skin_type or 'unknown'}."
    )

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=8.0,
        )
        resp = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "You respond with valid JSON only, no markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=300,
            timeout=8.0,
        )
        content = (resp.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        parsed = json.loads(content)
        parsed.setdefault("source", "ai")
        if r is not None:
            try:
                r.setex(cache_key, 86400, json.dumps(parsed))
            except Exception:
                pass
        return parsed
    except Exception:
        return None


@router.get("/coach")
async def get_coach(
    current_user: User = Depends(require_pro),
    db: Session = Depends(get_db),
):
    """Return today's coach message for a Pro/Elite user."""
    latest = (
        db.query(Photo)
        .filter(Photo.user_id == current_user.id, Photo.score.isnot(None))
        .order_by(Photo.captured_at.desc())
        .first()
    )

    score = latest.score if latest else None
    weakest: List[str] = []
    if latest and isinstance(latest.analysis_details, dict):
        breakdown = latest.analysis_details.get("category_breakdown") or {}
        if isinstance(breakdown, dict) and breakdown:
            weakest = sorted(breakdown, key=lambda k: breakdown.get(k, 0))[:2]

    tip = _deepseek_tip(current_user, score, weakest) or _fallback_tip(current_user, weakest, score)

    return {
        "date": datetime.utcnow().date().isoformat(),
        "tier": (current_user.subscription_tier or "free").lower(),
        "message": tip.get("message", ""),
        "focus": tip.get("focus"),
        "tasks": tip.get("tasks", []),
        "score_context": tip.get("score_context") or get_score_label(score if score is not None else 0)["label"],
        "source": tip.get("source", "template"),
    }
