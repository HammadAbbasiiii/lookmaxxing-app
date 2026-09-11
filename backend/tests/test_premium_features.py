"""Regression tests for the premium features (Coach / Insights / Harmony).

These reproduce the production data shape where ``analysis_details.category_breakdown``
is stored *nested* (``{category: {"score": float, "description": str}, "heuristic": ...}``)
rather than flat. Previously that shape raised ``TypeError`` in the coach, report,
insights and harmony endpoints (and silently emptied product recommendations).
"""

import pytest

from app.dependencies import create_access_token, get_password_hash
from app.models import Photo, User
from app.services.category_breakdown import normalize_breakdown
from app.routes.explore import _identity, _rank_label


NESTED_BREAKDOWN = {
    "facial_harmony": {"score": 80.0, "description": "Good facial harmony"},
    "skin_quality": {"score": 60.0, "description": "Good skin quality"},
    "jawline_definition": {"score": 65.0, "description": "Good jawline definition"},
    "eye_appeal": {"score": 70.0, "description": "Good eye appeal"},
    "facial_structure": {"score": 72.0, "description": "Good facial structure"},
    "masculinity_femininity": {"score": 68.0, "description": "Good gender appeal"},
    "heuristic": False,
}


def _elite(db_session):
    user = User(
        email="elite-regression@example.com",
        hashed_password=get_password_hash("pass1234"),
        full_name="ML",
        is_subscribed=True,
        subscription_tier="elite",
        current_day=14,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    photo = Photo(
        user_id=user.id,
        file_url="https://example.com/face.jpg",
        score=70.0,
        face_shape="oval",
        analysis_details={"category_breakdown": NESTED_BREAKDOWN},
    )
    db_session.add(photo)
    db_session.commit()
    db_session.refresh(photo)
    return user, photo


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user.id})}"}


def test_normalize_breakdown_accepts_both_shapes():
    assert normalize_breakdown(NESTED_BREAKDOWN) == {
        "facial_harmony": 80.0,
        "skin_quality": 60.0,
        "jawline_definition": 65.0,
        "eye_appeal": 70.0,
        "facial_structure": 72.0,
        "masculinity_femininity": 68.0,
    }
    assert normalize_breakdown({"skin_quality": 45}) == {"skin_quality": 45.0}
    assert normalize_breakdown(None) == {}
    assert normalize_breakdown("nope") == {}


def test_identity_uses_stable_pseudonym_and_rank():
    class U:
        def __init__(self, id_, full_name):
            self.id = id_
            self.full_name = full_name

    ml = _identity(U("user-ml-1", "ML"))
    hammad = _identity(U("user-hammad", "Hammad Khan"))
    empty = _identity(U("user-empty", None))

    # Every member gets a deterministic, privacy-safe pseudonym with initials —
    # no real first names, no confusing fake names like "Alex"/"Noah".
    assert ml["username"] and " " in ml["username"]
    assert len(ml["initials"]) == 2 and ml["initials"].isupper()
    assert hammad["username"] and hammad["initials"]
    assert empty["username"] and empty["initials"]
    assert ml == _identity(U("user-ml-1", "ML"))  # deterministic per user

    assert _rank_label(0.5) == "On the Rise"
    assert _rank_label(2.0) == "Most Improved"
    assert _rank_label(4.0) == "Rising Star"
    assert _rank_label(7.0) == "Glow-Up Legend"


def test_coach_loads_with_nested_breakdown(client, db_session, monkeypatch):
    user, _ = _elite(db_session)
    # Never call DeepSeek in tests — exercise the deterministic fallback.
    monkeypatch.setattr("app.routes.coach._deepseek_tip", lambda *a, **k: None)

    res = client.get("/api/v1/coach", headers=_headers(user))
    assert res.status_code == 200
    body = res.json()
    assert body["message"]
    assert body["focus"]
    assert isinstance(body["tasks"], list) and body["tasks"]


def test_insights_load_with_nested_breakdown(client, db_session):
    user, photo = _elite(db_session)
    res = client.get(f"/api/v1/analysis/{photo.id}/insights", headers=_headers(user))
    assert res.status_code == 200
    body = res.json()

    assert body["forecast"]["current_score"] == 70.0
    assert len(body["forecast"]["milestones"]) == 3
    assert body["archetype"]["name"]
    assert isinstance(body["archetype"]["reasons"], list) and body["archetype"]["reasons"]


def test_harmony_loads_with_nested_breakdown(client, db_session):
    user, photo = _elite(db_session)
    res = client.get(f"/api/v1/analysis/{photo.id}/harmony", headers=_headers(user))
    assert res.status_code == 200
    body = res.json()

    assert body["golden_ratio"]["phi_score"] is not None
    assert isinstance(body["golden_ratio"]["metrics"], list) and len(body["golden_ratio"]["metrics"]) >= 4
    assert len(body["blueprint"]["days"]) == 7
    assert body["glow_up_card"]["share_text"]


def test_report_loads_with_nested_breakdown(client, db_session):
    user, photo = _elite(db_session)
    res = client.get(f"/api/v1/analysis/{photo.id}/report", headers=_headers(user))
    assert res.status_code == 200
    body = res.json()

    scores = [c["score"] for c in body["categories"]]
    assert scores == sorted(scores)  # weakest-first ordering must survive
    assert all(isinstance(s, float) for s in scores)
    assert body["weakest_areas"] and body["strongest_areas"]


def test_product_recommendations_do_not_crash_with_nested_breakdown(client, db_session):
    user, _ = _elite(db_session)
    res = client.get("/api/v1/products/recommendations", headers=_headers(user))
    # Even if no products are seeded, this must not 500.
    assert res.status_code == 200
    assert res.json()["success"] is True
