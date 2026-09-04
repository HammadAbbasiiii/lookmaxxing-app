"""Premium gating, freemium limits, entitlements, payments and coach access."""

import pytest
from fastapi import HTTPException

from app.dependencies import create_access_token, get_password_hash
from app.models import Photo, User
from app.services.entitlements_service import (
    enforce_analysis_limit,
    enforce_photo_limit,
)


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _user(db_session, email, tier="free"):
    u = User(
        email=email,
        hashed_password=get_password_hash("pass1234"),
        full_name="Gate User",
        is_subscribed=tier != "free",
        subscription_tier=tier,
        current_day=0,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _scored_photo(db_session, user, score=70.0):
    p = Photo(user_id=user.id, file_url="https://example.com/x.jpg", score=score)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


class TestFreemiumLimits:
    def test_free_second_analysis_blocked(self, db_session):
        u = _user(db_session, "freelimit@example.com", "free")
        _scored_photo(db_session, u)
        with pytest.raises(HTTPException) as e:
            enforce_analysis_limit(u, db_session)
        assert e.value.status_code == 403
        assert e.value.detail["code"] == "upgrade_required"

    def test_free_first_analysis_allowed(self, db_session):
        u = _user(db_session, "freeok@example.com", "free")
        enforce_analysis_limit(u, db_session)  # no raise with 0 scored photos

    def test_pro_unlimited_analyses(self, db_session):
        u = _user(db_session, "prounlim@example.com", "pro")
        _scored_photo(db_session, u)
        _scored_photo(db_session, u)
        enforce_analysis_limit(u, db_session)  # no raise

    def test_free_photo_limit(self, db_session):
        u = _user(db_session, "freephoto@example.com", "free")
        _scored_photo(db_session, u)
        with pytest.raises(HTTPException) as e:
            enforce_photo_limit(u, db_session)
        assert e.value.status_code == 403

    def test_pro_no_photo_limit(self, db_session):
        u = _user(db_session, "prophoto@example.com", "pro")
        _scored_photo(db_session, u)
        enforce_photo_limit(u, db_session)  # no raise


class TestEntitlements:
    def test_free_entitlements(self, client, auth_token):
        res = client.get("/api/v1/entitlements", headers=_h(auth_token))
        assert res.status_code == 200
        body = res.json()
        assert body["tier"] == "free"
        assert body["limits"]["analyses"]["unlimited"] is False
        assert body["limits"]["analyses"]["allowed"] == 1
        assert body["limits"]["analyses"]["remaining"] == 1
        # Some features must be locked for free.
        assert any(f["locked"] for f in body["features"])

    def test_pro_entitlements(self, client, db_session):
        u = _user(db_session, "proent@example.com", "pro")
        res = client.get(
            "/api/v1/entitlements",
            headers=_h(create_access_token(data={"sub": u.id})),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["tier"] == "pro"
        assert body["limits"]["analyses"]["unlimited"] is True
        assert body["limits"]["analyses"]["allowed"] is None

    def test_elite_entitlements(self, client, db_session):
        u = _user(db_session, "eliteent@example.com", "elite")
        res = client.get(
            "/api/v1/entitlements",
            headers=_h(create_access_token(data={"sub": u.id})),
        )
        assert res.status_code == 200
        assert res.json()["tier"] == "elite"

    def test_entitlements_requires_auth(self, client):
        assert client.get("/api/v1/entitlements").status_code == 401


class TestCoachGating:
    def test_free_denied(self, client, auth_token):
        res = client.get("/api/v1/coach", headers=_h(auth_token))
        assert res.status_code == 403
        assert res.json()["detail"]["code"] == "upgrade_required"

    def test_pro_allowed(self, client, db_session):
        u = _user(db_session, "procoach@example.com", "pro")
        res = client.get(
            "/api/v1/coach", headers=_h(create_access_token(data={"sub": u.id}))
        )
        assert res.status_code == 200
        body = res.json()
        assert body["message"]
        assert isinstance(body["tasks"], list) and body["tasks"]


class TestPayments:
    def test_checkout_unconfigured(self, client, auth_token):
        res = client.post(
            "/api/v1/payments/checkout",
            json={"tier": "pro", "annual": True},
            headers=_h(auth_token),
        )
        assert res.status_code == 503
        assert res.json()["detail"]["code"] == "payments_unconfigured"

    def test_checkout_invalid_tier(self, client, auth_token):
        res = client.post(
            "/api/v1/payments/checkout",
            json={"tier": "premium", "annual": True},
            headers=_h(auth_token),
        )
        assert res.status_code == 422

    def test_checkout_requires_auth(self, client):
        res = client.post(
            "/api/v1/payments/checkout", json={"tier": "pro", "annual": True}
        )
        assert res.status_code == 401

    def test_test_upgrade_disabled(self, client, auth_token):
        res = client.post(
            "/api/v1/payments/test-upgrade",
            json={"tier": "pro"},
            headers=_h(auth_token),
        )
        assert res.status_code == 403
        assert res.json()["detail"]["code"] == "test_payments_disabled"

    def test_webhook_unconfigured(self, client):
        res = client.post("/api/v1/payments/webhook")
        assert res.status_code == 503


