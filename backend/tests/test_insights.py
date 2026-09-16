"""Tests for the creative premium insights endpoints (Pro/Elite).

Covers the gating and payload shape for:
  Pro   — GET /analysis/{photo_id}/insights  (forecast + percentile + archetype)
  Elite — GET /analysis/{photo_id}/harmony   (golden ratio + blueprint + card)

Plus deterministic service-level checks so the math stays honest:
  - forecast is monotonic and clamps to the potential score
  - rank_label thresholds
  - archetype is gender-aware
  - blueprint always returns 7 days
"""

import uuid
from datetime import datetime, timedelta

import pytest

from app.dependencies import create_access_token, get_password_hash
from app.models import Photo, Plan, User
from app.services.insights_service import (
    build_archetype,
    build_blueprint,
    build_forecast,
    rank_label,
)


def _make_user(db_session, email, tier):
    u = User(
        email=email,
        hashed_password=get_password_hash("pass1234"),
        full_name="Insight User",
        is_subscribed=tier != "free",
        subscription_tier=tier,
        current_day=0,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _add_photo(db_session, user, score=70.0):
    p = Photo(
        user_id=user.id,
        file_url="https://example.com/face.jpg",
        score=score,
        face_shape="oval",
        analysis_details={
            "category_breakdown": {
                "skin_quality": 60,
                "jawline_definition": 65,
                "facial_harmony": 80,
                "eye_appeal": 70,
                "facial_structure": 72,
                "masculinity_femininity": 68,
            }
        },
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}


# ── Gating ────────────────────────────────────────────────────────────
def test_insights_requires_pro(client, db_session, test_user):
    photo = _add_photo(db_session, test_user)
    res = client.get(f"/api/v1/analysis/{photo.id}/insights", headers=_headers(test_user))
    assert res.status_code == 403


def test_harmony_requires_elite(client, db_session):
    pro = _make_user(db_session, "pro@example.com", "pro")
    photo = _add_photo(db_session, pro)
    res = client.get(f"/api/v1/analysis/{photo.id}/harmony", headers=_headers(pro))
    assert res.status_code == 403


def test_insights_unknown_photo(client, db_session):
    pro = _make_user(db_session, "pro2@example.com", "pro")
    res = client.get("/api/v1/analysis/does-not-exist/insights", headers=_headers(pro))
    assert res.status_code == 404


# ── Pro insights payload ──────────────────────────────────────────────
def test_insights_shape(client, db_session):
    pro = _make_user(db_session, "pro3@example.com", "pro")
    photo = _add_photo(db_session, pro, score=70.0)
    res = client.get(f"/api/v1/analysis/{photo.id}/insights", headers=_headers(pro))
    assert res.status_code == 200
    body = res.json()

    assert body["photo_id"] == photo.id
    assert "forecast" in body and "percentile" in body and "archetype" in body

    forecast = body["forecast"]
    assert forecast["current_score"] == 70.0
    assert forecast["potential_score"] > 70.0
    assert len(forecast["milestones"]) == 3
    assert forecast["milestones"][-1]["day"] == 90

    assert "percentile" in body["percentile"]
    assert "rank_label" in body["percentile"]

    archetype = body["archetype"]
    assert archetype["name"]
    assert isinstance(archetype["reasons"], list) and archetype["reasons"]


# ── Elite harmony payload ─────────────────────────────────────────────
def test_harmony_shape(client, db_session):
    elite = _make_user(db_session, "elite@example.com", "elite")
    photo = _add_photo(db_session, elite, score=80.0)
    res = client.get(f"/api/v1/analysis/{photo.id}/harmony", headers=_headers(elite))
    assert res.status_code == 200
    body = res.json()

    assert body["photo_id"] == photo.id
    assert "golden_ratio" in body and "blueprint" in body and "glow_up_card" in body

    golden = body["golden_ratio"]
    assert golden["phi_score"] is not None
    assert isinstance(golden["metrics"], list) and len(golden["metrics"]) >= 4

    blueprint = body["blueprint"]
    assert len(blueprint["days"]) == 7
    assert blueprint["gender_note"]

    card = body["glow_up_card"]
    assert card["score"] == 80.0
    assert card["archetype"] and card["share_text"]


# ── Service determinism ───────────────────────────────────────────────
def test_forecast_monotonic_and_capped():
    f = build_forecast(60.0, 0)
    scores = [m["projected_score"] for m in f["milestones"]]
    assert scores == sorted(scores)
    assert scores[-1] == f["potential_score"]


def test_rank_label_thresholds():
    assert rank_label(99.5) == "Top 1%"
    assert rank_label(95.0) == "Top 5%"
    assert rank_label(90.0) == "Top 10%"
    assert rank_label(75.0) == "Top 25%"
    assert rank_label(50.0) == "Above average"
    assert rank_label(10.0) == "Rising Star"
    assert rank_label(None) == "—"


def test_archetype_is_gender_aware():
    male = build_archetype(75.0, "square", "male", {})
    female = build_archetype(75.0, "square", "female", {})
    assert male["name"] == "The Athlete"
    assert female["name"] == "The Boss"


def test_blueprint_always_seven_days():
    b = build_blueprint([], "male")
    assert len(b["days"]) == 7
    assert all(d["day"] == i + 1 for i, d in enumerate(b["days"]))
    assert all(d["focus"] and d["task"] for d in b["days"])


def test_blueprint_week_never_repeats_a_task():
    """Cycling only the three weakest focuses repeated the same three tasks
    across the week (days 1-3 showed up again as days 4-6, and once more on 7)."""
    b = build_blueprint(["facial_harmony", "jawline_definition", "eye_appeal"], "male")
    tasks = [d["task"] for d in b["days"]]
    assert len(tasks) == 7
    assert len(set(tasks)) == 7


def test_rank_withheld_below_minimum_peer_sample(client, db_session):
    """With a handful of peers the top scorer always computes to the 100th
    percentile, i.e. "Top 1%" — a claim we can't back up, so withhold it."""
    pro = _make_user(db_session, "ranked@example.com", "pro")
    peer = _make_user(db_session, "peer@example.com", "free")
    _add_photo(db_session, peer, score=50.0)
    photo = _add_photo(db_session, pro, score=70.0)

    res = client.get(f"/api/v1/analysis/{photo.id}/insights", headers=_headers(pro))
    assert res.status_code == 200

    percentile = res.json()["percentile"]
    assert percentile["peer_count"] == 1
    assert percentile["percentile"] is None
    assert percentile["rank_label"] == "—"


def test_glow_up_card_day_follows_the_plan_calendar(client, db_session):
    """`User.current_day` only moves on check-in, so the shareable card must read
    the day from the active plan — otherwise it advertises "Day 0/90" for a user
    who is weeks in."""
    elite = _make_user(db_session, "elite-card@example.com", "elite")
    photo = _add_photo(db_session, elite, score=80.0)

    db_session.add(
        Plan(
            id=str(uuid.uuid4()),
            user_id=elite.id,
            created_at=datetime.utcnow() - timedelta(days=12),
            current_day=0,
            is_active=True,
        )
    )
    db_session.commit()

    res = client.get(f"/api/v1/analysis/{photo.id}/harmony", headers=_headers(elite))
    assert res.status_code == 200

    card = res.json()["glow_up_card"]
    assert card["day"] == 13
    assert "Day 13/90" in card["share_text"]
